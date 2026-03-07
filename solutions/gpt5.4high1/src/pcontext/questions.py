from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar, Annotated, get_args, get_origin, get_type_hints

from pydantic import TypeAdapter

from pcontext.config import get_paths
from pcontext.runtime.discovery import read_agent_endpoint
from pcontext.runtime.ipc_client import send_request
from pcontext.runtime.ipc_models import ErrorResponse
from pcontext.runtime.question_models import (
    AskUserRequest,
    AskUserResponse,
    QuestionFieldSchema,
    QuestionFormSchema,
)


@dataclass(frozen=True, slots=True)
class Question:
    """
    Описание одного поля в форме вопросов.
    """

    title: str | None = None
    description: str | None = None
    ge: float | None = None
    gt: float | None = None
    le: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    format: type[object] | None = None


class Questions:
    """
    Базовый класс для декларативной формы вопросов.
    """


class ImageQuery:
    """
    Маркер формата поля: ожидается путь к изображению.
    """


_TQuestions = TypeVar("_TQuestions", bound=Questions)
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _QuestionFieldDefinition:
    """
    Внутреннее описание поля Questions-класса.
    """

    name: str
    base_annotation: Any
    schema: QuestionFieldSchema
    default_value: Any


def _unwrap_annotated(annotation: Any) -> tuple[Any, list[Any]]:
    """
    Разворачивает `Annotated[T, ...]`.
    """
    if get_origin(annotation) is Annotated:
        parts = list(get_args(annotation))
        return parts[0], parts[1:]

    return annotation, []


def _display_type_name(annotation: Any) -> str:
    """
    Возвращает человекочитаемое имя типа.
    """
    if annotation is str:
        return "str"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation is Path:
        return "pathlib.Path"

    if inspect.isclass(annotation):
        return f"{annotation.__module__}.{annotation.__qualname__}"

    return repr(annotation)


def _question_value_kind(annotation: Any) -> tuple[str, list[Any]]:
    """
    Определяет тип поля для GUI-формы.
    """
    if annotation is str:
        return "str", []

    if annotation is int:
        return "int", []

    if annotation is float:
        return "float", []

    if annotation is bool:
        return "bool", []

    if annotation is Path:
        return "path", []

    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return "enum", [member.value for member in annotation]

    return "unknown", []


def _build_field_definition(
    model_type: type[Questions],
    field_name: str,
    annotation: Any,
) -> _QuestionFieldDefinition:
    """
    Преобразует одно аннотированное поле Questions-класса
    во внутреннее описание и GUI-схему.
    """
    base_annotation, metadata_items = _unwrap_annotated(annotation)

    question_metadata = Question()
    string_metadata: list[str] = []

    for item in metadata_items:
        if isinstance(item, Question):
            question_metadata = item
            continue

        if isinstance(item, str):
            string_metadata.append(item)
            continue

        if item is ImageQuery:
            question_metadata = Question(
                title=question_metadata.title,
                description=question_metadata.description,
                ge=question_metadata.ge,
                gt=question_metadata.gt,
                le=question_metadata.le,
                lt=question_metadata.lt,
                min_length=question_metadata.min_length,
                max_length=question_metadata.max_length,
                pattern=question_metadata.pattern,
                format=ImageQuery,
            )

    title = question_metadata.title or (
        string_metadata[0] if string_metadata else field_name
    )
    description = question_metadata.description
    if description is None and len(string_metadata) > 1:
        description = string_metadata[1]

    raw_default = getattr(model_type, field_name, _MISSING)
    required = raw_default is _MISSING
    default_value = None if required else raw_default

    value_kind, enum_values = _question_value_kind(base_annotation)
    field_format = "image_path" if question_metadata.format is ImageQuery else None

    schema = QuestionFieldSchema(
        name=field_name,
        title=title,
        description=description,
        value_kind=value_kind,
        display_name=_display_type_name(base_annotation),
        required=required,
        default_value=default_value if not required else None,
        enum_values=enum_values,
        ge=question_metadata.ge,
        gt=question_metadata.gt,
        le=question_metadata.le,
        lt=question_metadata.lt,
        min_length=question_metadata.min_length,
        max_length=question_metadata.max_length,
        pattern=question_metadata.pattern,
        format=field_format,
    )

    return _QuestionFieldDefinition(
        name=field_name,
        base_annotation=base_annotation,
        schema=schema,
        default_value=default_value,
    )


def _iter_question_fields(
    model_type: type[Questions],
) -> list[_QuestionFieldDefinition]:
    """
    Возвращает список полей Questions-класса в порядке объявления.
    """
    annotations = getattr(model_type, "__annotations__", {})
    type_hints = get_type_hints(model_type, include_extras=True)

    result: list[_QuestionFieldDefinition] = []

    for field_name in annotations:
        annotation = type_hints.get(field_name, annotations[field_name])
        result.append(_build_field_definition(model_type, field_name, annotation))

    return result


def _build_question_form_schema(model_type: type[Questions]) -> QuestionFormSchema:
    """
    Строит сериализуемую GUI-схему формы вопросов.
    """
    fields = _iter_question_fields(model_type)

    return QuestionFormSchema(
        model_name=model_type.__name__,
        title=model_type.__name__,
        fields=[field.schema for field in fields],
    )


def _validate_answers(
    model_type: type[_TQuestions],
    raw_answers: dict[str, object],
) -> dict[str, Any]:
    """
    Приводит ответы пользователя к объявленным Python-типам.
    """
    validated: dict[str, Any] = {}

    for field in _iter_question_fields(model_type):
        if field.name in raw_answers:
            raw_value = raw_answers[field.name]
        elif field.schema.required:
            raise ValueError(
                f"В ответах пользователя отсутствует обязательное поле '{field.name}'."
            )
        else:
            raw_value = field.default_value

        adapter = TypeAdapter(field.base_annotation)
        validated[field.name] = adapter.validate_python(raw_value)

    return validated


def _instantiate_questions_model(
    model_type: type[_TQuestions],
    values: dict[str, Any],
) -> _TQuestions:
    """
    Создаёт экземпляр Questions-класса и заполняет его полями.
    """
    instance = model_type.__new__(model_type)

    for field_name, value in values.items():
        setattr(instance, field_name, value)

    return instance


def Ask(model_type: type[_TQuestions]) -> _TQuestions | None:
    """
    Запрашивает у пользователя ответы на вопросы.

    Эта функция вызывается из worker/service-host процесса и синхронно
    обращается к уже запущенному GUI-агенту PContext.
    """
    endpoint = read_agent_endpoint(get_paths().agent_endpoint)

    response = send_request(
        endpoint,
        AskUserRequest(
            token=endpoint.token,
            form_schema=_build_question_form_schema(model_type),
        ),
        timeout_seconds=3600.0,
    )

    if isinstance(response, ErrorResponse):
        raise RuntimeError(response.message)

    if not isinstance(response, AskUserResponse):
        raise RuntimeError("Агент вернул неожиданный ответ на Ask-запрос.")

    if response.cancelled:
        return None

    validated_answers = _validate_answers(model_type, response.answers)
    return _instantiate_questions_model(model_type, validated_answers)
