from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class StrictModel(BaseModel):
    """
    Базовая строгая модель для схемы Ask-диалогов.
    """

    model_config = ConfigDict(extra="forbid")


class QuestionFieldSchema(StrictModel):
    """
    Описание одного поля формы вопросов.
    """

    name: str
    title: str
    description: str | None = None
    value_kind: Literal["str", "int", "float", "bool", "enum", "path", "unknown"]
    display_name: str
    required: bool = True
    default_value: Any | None = None
    enum_values: list[Any] = Field(default_factory=list)
    ge: float | None = None
    gt: float | None = None
    le: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    format: Literal["image_path"] | None = None


class QuestionFormSchema(StrictModel):
    """
    Полная схема Ask-формы.
    """

    model_name: str
    title: str
    fields: list[QuestionFieldSchema]


class AskUserRequest(StrictModel):
    """
    IPC-запрос от worker/service-host к агенту:
    попросить пользователя заполнить форму.
    """

    kind: Literal["ask_user"] = "ask_user"
    protocol_version: Literal[1] = 1
    token: str
    form_schema: QuestionFormSchema


class AskUserResponse(StrictModel):
    """
    Ответ агента на Ask-запрос.
    """

    kind: Literal["ask_user_result"] = "ask_user_result"
    ok: Literal[True] = True
    protocol_version: Literal[1] = 1
    cancelled: bool
    answers: dict[str, Any] = Field(default_factory=dict)


AskRuntimeMessage: TypeAlias = Annotated[
    AskUserRequest | AskUserResponse,
    Field(discriminator="kind"),
]

ASK_RUNTIME_ADAPTER = TypeAdapter(AskRuntimeMessage)
