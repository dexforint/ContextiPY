from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from pcontext.actions import (
    ActionResult,
    Copy,
    Folder as FolderAction,
    Link,
    Notify,
    Open,
    Text,
)


class StrictModel(BaseModel):
    """
    Базовая модель сериализуемого действия.

    Лишние поля запрещены, чтобы формат не расползался.
    """

    model_config = ConfigDict(extra="forbid")


class NoneAction(StrictModel):
    """
    Скрипт завершился без дополнительного действия.
    """

    kind: Literal["none"] = "none"


class OpenAction(StrictModel):
    """
    Открыть файл через приложение по умолчанию
    или через явно указанную программу.
    """

    kind: Literal["open"] = "open"
    path: str
    app: str | None = None


class TextAction(StrictModel):
    """
    Показать текст пользователю.
    """

    kind: Literal["text"] = "text"
    text: str
    title: str | None = None


class LinkAction(StrictModel):
    """
    Открыть ссылку.
    """

    kind: Literal["link"] = "link"
    url: str


class CopyAction(StrictModel):
    """
    Скопировать текст в буфер обмена.
    """

    kind: Literal["copy"] = "copy"
    text: str
    notification: str | None = None


class NotifyAction(StrictModel):
    """
    Показать уведомление.
    """

    kind: Literal["notify"] = "notify"
    title: str
    description: str | None = None


class FolderActionModel(StrictModel):
    """
    Открыть папку.
    """

    kind: Literal["folder"] = "folder"
    path: str


SerializedAction: TypeAlias = Annotated[
    NoneAction
    | OpenAction
    | TextAction
    | LinkAction
    | CopyAction
    | NotifyAction
    | FolderActionModel,
    Field(discriminator="kind"),
]

SERIALIZED_ACTION_ADAPTER = TypeAdapter(SerializedAction)


def _path_to_string(value: str | Path | None) -> str | None:
    """
    Нормализует путь в строку.
    """
    if value is None:
        return None
    return str(value)


def serialize_action_result(action: ActionResult) -> SerializedAction:
    """
    Преобразует Python-объект действия в JSON-совместимую модель.
    """
    if action is None:
        return NoneAction()

    if isinstance(action, Open):
        return OpenAction(
            path=str(action.path),
            app=_path_to_string(action.app),
        )

    if isinstance(action, Text):
        return TextAction(
            text=action.text,
            title=action.title,
        )

    if isinstance(action, Link):
        return LinkAction(url=action.url)

    if isinstance(action, Copy):
        return CopyAction(
            text=action.text,
            notification=action.notification,
        )

    if isinstance(action, Notify):
        return NotifyAction(
            title=action.title,
            description=action.description,
        )

    if isinstance(action, FolderAction):
        return FolderActionModel(path=str(action.path))

    raise TypeError(
        "Скрипт вернул неподдерживаемый тип результата. "
        "Ожидается одно из действий PContext или None."
    )


def describe_serialized_action(action: SerializedAction) -> str:
    """
    Возвращает короткое человекочитаемое описание действия.
    """
    if isinstance(action, NoneAction):
        return "Дополнительное действие отсутствует."

    if isinstance(action, OpenAction):
        return f"Возвращено действие Open для пути: {action.path}"

    if isinstance(action, TextAction):
        return "Возвращено действие Text."

    if isinstance(action, LinkAction):
        return f"Возвращено действие Link: {action.url}"

    if isinstance(action, CopyAction):
        return "Возвращено действие Copy."

    if isinstance(action, NotifyAction):
        return f"Возвращено действие Notify: {action.title}"

    if isinstance(action, FolderActionModel):
        return f"Возвращено действие Folder для пути: {action.path}"

    return "Возвращено неизвестное действие."
