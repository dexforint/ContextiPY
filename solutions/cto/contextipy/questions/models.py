from __future__ import annotations

"""Question models, schema extraction, and validation utilities."""

from dataclasses import MISSING, dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, TypeVar, get_args, get_origin

from .types import ImageQuery, Question, UNSET, _UnsetType


TQuestions = TypeVar("TQuestions", bound="Questions")


@dataclass(frozen=True)
class QuestionDefinition:
    """Resolved metadata for a single question field."""

    name: str
    question: Question[Any]
    annotation: Any
    required: bool
    default: Any
    optional: bool

    def has_default(self) -> bool:
        return self.default is not UNSET

    def to_ui_payload(self) -> dict[str, Any]:
        """Produce a serialisable payload describing the question."""

        descriptor: dict[str, Any] = {
            "name": self.name,
            "title": self.question.title,
            "kind": self.question.kind,
            "required": self.required,
        }

        if self.question.description:
            descriptor["description"] = self.question.description

        if self.has_default():
            descriptor["default"] = self.question.serialize(self.default)

        if self.question.enum is not None:
            descriptor["enum"] = [self.question.serialize(value) for value in self.question.enum]

        if self.question.ge is not None:
            descriptor["ge"] = self.question.ge

        if self.question.le is not None:
            descriptor["le"] = self.question.le

        if isinstance(self.question, ImageQuery):
            descriptor["formats"] = self.question.formats

        return descriptor

    def resolve(self, answers: Mapping[str, Any]) -> Any:
        """Resolve a value from answer payloads while applying validation."""

        sentinel = object()
        raw_value = answers.get(self.name, sentinel)

        if raw_value is sentinel:
            if self.has_default():
                value = self.default
            elif not self.required:
                return None
            else:
                msg = f"Question '{self.name}' requires a value"
                raise ValueError(msg)
        else:
            value = raw_value

        if isinstance(value, _UnsetType):
            if self.has_default():
                value = self.default
            elif not self.required:
                return None
            else:
                msg = f"Question '{self.name}' requires a value"
                raise ValueError(msg)

        if value is None:
            if self.required:
                msg = f"Question '{self.name}' requires a non-null value"
                raise ValueError(msg)
            return None

        converted = self.question.deserialize(value)
        coerced = _coerce_to_annotation(self.annotation, converted, self.name)
        validated = _apply_constraints(self.question, coerced, self.name)
        return validated


class Questions:
    """Base class for declarative question groups defined as dataclasses."""

    @classmethod
    def definitions(cls) -> tuple[QuestionDefinition, ...]:
        return _extract_definitions(cls)

    @classmethod
    def ui_schema(cls) -> list[dict[str, Any]]:
        return [definition.to_ui_payload() for definition in cls.definitions()]

    @classmethod
    def validate_answers(cls, answers: Mapping[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for definition in cls.definitions():
            resolved[definition.name] = definition.resolve(answers)
        return resolved

    @classmethod
    def from_answers(cls: type[TQuestions], answers: Mapping[str, Any]) -> TQuestions:
        validated = cls.validate_answers(answers)
        return cls(**validated)


def Ask(question_cls: type[TQuestions]) -> TQuestions | None:
    """Render questions using the UI module and return validated answers."""

    if not issubclass(question_cls, Questions):
        msg = "Ask() expects a subclass of Questions"
        raise TypeError(msg)

    schema = question_cls.ui_schema()

    from . import ui

    answers = ui.ask(schema)
    if answers is None:
        return None

    validated = question_cls.validate_answers(dict(answers))
    return question_cls(**validated)


def _extract_definitions(target: type[Questions]) -> tuple[QuestionDefinition, ...]:
    if not is_dataclass(target):
        msg = "Questions subclasses must be defined as dataclasses"
        raise TypeError(msg)

    type_hints = getattr(target, "__annotations__", {})
    evaluated_hints = _evaluate_type_hints(target)

    definitions: list[QuestionDefinition] = []

    for field in fields(target):
        annotation = evaluated_hints.get(field.name, type_hints.get(field.name))
        if annotation is None:
            continue

        question, raw_annotation = _question_from_annotation(annotation, target.__name__, field.name)

        base_annotation, optional = _strip_optional(raw_annotation)

        default_value = _resolve_default(field, question)
        if default_value is not UNSET:
            default_value = _prepare_value(question, base_annotation, default_value, field.name)

        required = question.required
        if default_value is not UNSET or optional:
            required = False

        definitions.append(
            QuestionDefinition(
                name=field.name,
                question=question,
                annotation=base_annotation,
                required=required,
                default=default_value,
                optional=optional or (default_value is not UNSET) or not required,
            )
        )

    return tuple(definitions)


def _evaluate_type_hints(target: type[Any]) -> dict[str, Any]:
    try:
        # include_extras ensures Annotated metadata is preserved
        from typing import get_type_hints

        return get_type_hints(target, include_extras=True)
    except TypeError:
        # Fallback for Python versions / constructs where evaluation fails
        return dict(getattr(target, "__annotations__", {}))


def _question_from_annotation(annotation: Any, cls_name: str, field_name: str) -> tuple[Question[Any], Any]:
    origin = get_origin(annotation)
    if origin is None:
        msg = f"{cls_name}.{field_name} must use typing.Annotated with Question metadata"
        raise TypeError(msg)

    from typing import Annotated

    if origin is not Annotated:
        msg = f"{cls_name}.{field_name} must be Annotated with a Question"
        raise TypeError(msg)

    args = get_args(annotation)
    if not args:
        msg = f"{cls_name}.{field_name} is missing Annotated metadata"
        raise TypeError(msg)

    base_annotation = args[0]
    question = next((meta for meta in args[1:] if isinstance(meta, Question)), None)
    if question is None:
        msg = f"{cls_name}.{field_name} is missing Question metadata"
        raise TypeError(msg)

    return question, base_annotation


def _strip_optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    if origin is None:
        return annotation, False

    args = get_args(annotation)
    if not args:
        return annotation, False

    non_none = [arg for arg in args if arg is not type(None)]  # noqa: E721
    if len(non_none) == len(args):
        return annotation, False

    if len(non_none) == 1:
        return non_none[0], True

    return annotation, False


def _resolve_default(field: Any, question: Question[Any]) -> Any:
    if question.has_default:
        if field.default is not MISSING or field.default_factory is not MISSING:  # type: ignore[attr-defined]
            msg = (
                f"{field.name}: default defined both in Question metadata and dataclass field"
            )
            raise ValueError(msg)
        return question.default

    if field.default is not MISSING:
        return field.default

    if field.default_factory is not MISSING:  # type: ignore[attr-defined]
        return field.default_factory()  # type: ignore[attr-defined]

    return UNSET


def _prepare_value(question: Question[Any], annotation: Any, value: Any, name: str) -> Any:
    if isinstance(value, _UnsetType):
        return UNSET

    converted = question.deserialize(value)
    coerced = _coerce_to_annotation(annotation, converted, name)
    return _apply_constraints(question, coerced, name)


def _coerce_to_annotation(annotation: Any, value: Any, name: str) -> Any:
    if value is None:
        return None

    if annotation is Any:
        return value

    origin = get_origin(annotation)
    if origin is not None:
        from typing import Literal

        if origin is Literal:
            choices = get_args(annotation)
            if value not in choices:
                msg = f"{name}: value must be one of {choices}"
                raise ValueError(msg)
            return value
        # For other typing constructs, return value as-is
        return value

    if isinstance(annotation, type):
        if issubclass(annotation, Path):
            if isinstance(value, Path):
                return value
            if not isinstance(value, str):
                msg = f"{name}: expected path string"
                raise TypeError(msg)
            return annotation(value)

        if issubclass(annotation, Enum):
            return _coerce_enum(annotation, value, name)

        if annotation in {int, float}:
            if isinstance(value, annotation):
                return value
            try:
                return annotation(value)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                msg = f"{name}: value {value!r} cannot be converted to {annotation.__name__}"
                raise TypeError(msg) from exc

        if annotation is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
            if isinstance(value, int):
                return bool(value)
            msg = f"{name}: value {value!r} cannot be converted to bool"
            raise TypeError(msg)

        if isinstance(value, annotation):
            return value

    return value


def _coerce_enum(enum_cls: type[Any], value: Any, name: str) -> Any:
    if isinstance(value, enum_cls):
        return value

    if isinstance(value, Enum):
        try:
            return enum_cls[value.name]
        except KeyError as exc:
            msg = f"{name}: {value} is not a valid member of {enum_cls.__name__}"
            raise TypeError(msg) from exc

    if isinstance(value, str):
        try:
            return enum_cls[value]
        except KeyError:
            pass
        for member in enum_cls:  # type: ignore[attr-defined]
            if str(member.value) == value:
                return member

    for member in enum_cls:  # type: ignore[attr-defined]
        if member.value == value:
            return member

    msg = f"{name}: {value!r} is not a valid member of {enum_cls.__name__}"
    raise TypeError(msg)


def _apply_constraints(question: Question[Any], value: Any, name: str) -> Any:
    if value is None:
        return None

    if question.enum is not None and value not in question.enum:
        msg = f"{name}: value must be one of {tuple(question.enum)}"
        raise ValueError(msg)

    if question.ge is not None:
        if not isinstance(value, (int, float)):
            msg = f"{name}: expected numeric type for lower bound"
            raise TypeError(msg)
        if value < question.ge:
            msg = f"{name}: value {value} must be >= {question.ge}"
            raise ValueError(msg)

    if question.le is not None:
        if not isinstance(value, (int, float)):
            msg = f"{name}: expected numeric type for upper bound"
            raise TypeError(msg)
        if value > question.le:
            msg = f"{name}: value {value} must be <= {question.le}"
            raise ValueError(msg)

    return value


__all__ = [
    "QuestionDefinition",
    "Questions",
    "Ask",
]
