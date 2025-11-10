"""Tests for Contextipy action serialisation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextipy.actions import (
    Copy,
    Folder,
    Link,
    NoneAction,
    Notify,
    Open,
    Text,
    serialize_action_for_log,
    serialize_actions_for_log,
)


class TestSerializeAction:
    """Unit tests covering individual action serialisation."""

    def test_serialize_open_action(self, tmp_path: Path) -> None:
        """Open actions should include their target path."""

        target = tmp_path / "document.txt"
        target.write_text("example")
        payload = serialize_action_for_log(Open(target))
        assert payload["type"] == "open"
        assert payload["target"] == str(target)

    def test_serialize_copy_action_redacted(self) -> None:
        """Textual values are redacted by default."""

        payload = serialize_action_for_log(Copy("secret"))
        assert payload == {"type": "copy", "text": "<redacted>"}

    def test_serialize_copy_action_full(self) -> None:
        """Textual values can be emitted when redaction is disabled."""

        payload = serialize_action_for_log(Copy("visible"), redacted=False)
        assert payload == {"type": "copy", "text": "visible"}

    @pytest.mark.parametrize(
        "action, expected",
        [
            (Text("hello"), {"type": "text", "content": "<redacted>"}),
            (Link("https://example.com"), {"type": "link", "url": "https://example.com"}),
            (
                Notify("Title", "Message"),
                {"type": "notify", "title": "Title", "message": "<redacted>"},
            ),
            (NoneAction("done"), {"type": "none", "reason": "done"}),
        ],
    )
    def test_various_actions_serialise(self, action, expected) -> None:
        """Ensure the remaining action types serialise as intended."""

        payload = serialize_action_for_log(action)
        assert payload == expected

    def test_serialize_folder_action(self, tmp_path: Path) -> None:
        """Folder actions should include the directory path."""

        folder = tmp_path / "data"
        folder.mkdir()
        payload = serialize_action_for_log(Folder(folder))
        assert payload == {"type": "folder", "target": str(folder)}

    def test_serialize_text_action_without_redaction(self) -> None:
        """Text content should be visible when redaction is disabled."""

        payload = serialize_action_for_log(Text("plaintext"), redacted=False)
        assert payload == {"type": "text", "content": "plaintext"}

    def test_serialize_notify_without_message(self) -> None:
        """Notify without message should exclude message key."""

        payload = serialize_action_for_log(Notify("Title"))
        assert payload == {"type": "notify", "title": "Title"}

    def test_serialize_none_action_without_reason(self) -> None:
        """NoneAction without reason should exclude reason key."""

        payload = serialize_action_for_log(NoneAction())
        assert payload == {"type": "none"}


class TestSerializeActions:
    """Tests for serialising collections of actions."""

    def test_serialize_multiple_actions(self, tmp_path: Path) -> None:
        """Serialising multiple actions should preserve order."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("value")
        actions = [Open(file_path), Copy("clip"), NoneAction()]
        payload = serialize_actions_for_log(actions)
        assert payload == [
            {"type": "open", "target": str(file_path)},
            {"type": "copy", "text": "<redacted>"},
            {"type": "none"},
        ]

    def test_serialize_multiple_without_redaction(self, tmp_path: Path) -> None:
        """Redaction flag applies to lists as well."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("value")
        actions = [Text("hello"), Notify("Title", "Body")]
        payload = serialize_actions_for_log(actions, redacted=False)
        assert payload == [
            {"type": "text", "content": "hello"},
            {"type": "notify", "title": "Title", "message": "Body"},
        ]
