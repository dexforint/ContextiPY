"""Action representations used by Contextipy.

This module defines a set of lightweight action objects that can be logged or
executed by other subsystems. Actions are intentionally simple dataclasses that
capture the minimum amount of information necessary to carry out a user intent.
They are accompanied by helpers that can serialise instances into structures
that are suitable for structured logging.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping, MutableMapping


_REDACTED = "<redacted>"


@dataclass(frozen=True, slots=True)
class Open:
    """Open a file-like resource using the system handler."""

    target: Path
    action_type: ClassVar[str] = "open"


@dataclass(frozen=True, slots=True)
class Text:
    """Return or display a block of text."""

    content: str
    action_type: ClassVar[str] = "text"


@dataclass(frozen=True, slots=True)
class Link:
    """Open a web link in the user's browser."""

    url: str
    action_type: ClassVar[str] = "link"


@dataclass(frozen=True, slots=True)
class Copy:
    """Copy text into the user's clipboard."""

    text: str
    action_type: ClassVar[str] = "copy"


@dataclass(frozen=True, slots=True)
class Notify:
    """Fire a user-visible notification."""

    title: str
    message: str | None = None
    action_type: ClassVar[str] = "notify"


@dataclass(frozen=True, slots=True)
class Folder:
    """Open a folder in the system file explorer."""

    target: Path
    action_type: ClassVar[str] = "folder"


@dataclass(frozen=True, slots=True)
class NoneAction:
    """Represents an absence of action."""

    reason: str | None = None
    action_type: ClassVar[str] = "none"


Action = Open | Text | Link | Copy | Notify | Folder | NoneAction


def _as_mutable_mapping(base: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """Return a mutable copy of *base*.

    The helper keeps type-checkers satisfied while guaranteeing that callers of
    the serialisation helpers receive a structure they can mutate if needed.
    """

    return dict(base)


def serialize_action_for_log(action: Action, *, redacted: bool = True) -> MutableMapping[str, Any]:
    """Serialise *action* into a structure appropriate for logging.

    Parameters
    ----------
    action:
        The action instance to serialise.
    redacted:
        When ``True`` (the default) potentially sensitive textual content is
        replaced with ``"<redacted>"`` so that logs do not leak user data.
    """

    payload: MutableMapping[str, Any] = _as_mutable_mapping({"type": action.action_type})

    if isinstance(action, (Open, Folder)):
        payload["target"] = str(action.target)
    elif isinstance(action, Link):
        payload["url"] = action.url
    elif isinstance(action, Text):
        payload["content"] = action.content if not redacted else _REDACTED
    elif isinstance(action, Copy):
        payload["text"] = action.text if not redacted else _REDACTED
    elif isinstance(action, Notify):
        payload["title"] = action.title
        if action.message is not None:
            payload["message"] = action.message if not redacted else _REDACTED
    elif isinstance(action, NoneAction):
        if action.reason is not None:
            payload["reason"] = action.reason

    return payload


def serialize_actions_for_log(
    actions: Iterable[Action], *, redacted: bool = True
) -> list[MutableMapping[str, Any]]:
    """Serialise a sequence of actions for logging purposes."""

    return [serialize_action_for_log(action, redacted=redacted) for action in actions]


__all__ = [
    "Action",
    "Open",
    "Text",
    "Link",
    "Copy",
    "Notify",
    "Folder",
    "NoneAction",
    "serialize_action_for_log",
    "serialize_actions_for_log",
]
