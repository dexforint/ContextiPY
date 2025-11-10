"""Tests for Contextipy action handler."""

from __future__ import annotations

from pathlib import Path

from contextipy.actions import Copy, Folder, Link, NoneAction, Notify, Open, Text
from contextipy.execution.action_handler import ActionHandler, ActionResult


class StubClipboard:
    """Test clipboard implementation."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.last_text: str | None = None

    def copy_text(self, text: str) -> ActionResult:
        if self.should_fail:
            return ActionResult(success=False, message="Clipboard failed")
        self.last_text = text
        return ActionResult(success=True, message="Copied to clipboard")


class StubNotification:
    """Test notification implementation."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.last_title: str | None = None
        self.last_message: str | None = None

    def show_notification(self, title: str, message: str | None = None) -> ActionResult:
        if self.should_fail:
            return ActionResult(success=False, message="Notification failed")
        self.last_title = title
        self.last_message = message
        return ActionResult(success=True, message="Notification shown")


class StubFileOpener:
    """Test file opener implementation."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.opened_paths: list[Path] = []

    def open_path(self, path: Path) -> ActionResult:
        if self.should_fail:
            return ActionResult(success=False, message="File opener failed")
        self.opened_paths.append(path)
        return ActionResult(success=True, message=f"Opened {path}")


class TestActionHandlerDryRun:
    """Tests for dry-run mode where no OS-level operations occur."""

    def test_dry_run_open(self, tmp_path: Path) -> None:
        """Dry-run mode should skip actual file opening."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener, dry_run=True)
        result = handler.execute(Open(file_path))
        assert result.success is True
        assert "Dry-run" in result.message
        assert opener.opened_paths == []

    def test_dry_run_copy(self) -> None:
        """Dry-run mode should skip actual clipboard operations."""

        clipboard = StubClipboard()
        handler = ActionHandler(clipboard=clipboard, dry_run=True)
        result = handler.execute(Copy("text"))
        assert result.success is True
        assert "Dry-run" in result.message
        assert clipboard.last_text is None

    def test_dry_run_notify(self) -> None:
        """Dry-run mode should skip actual notifications."""

        notification = StubNotification()
        handler = ActionHandler(notification=notification, dry_run=True)
        result = handler.execute(Notify("Title", "Message"))
        assert result.success is True
        assert "Dry-run" in result.message
        assert notification.last_title is None


class TestActionHandlerOpen:
    """Tests for Open action handling."""

    def test_open_existing_file(self, tmp_path: Path) -> None:
        """Open should succeed for existing files."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Open(file_path))
        assert result.success is True
        assert opener.opened_paths == [file_path]

    def test_open_missing_file(self, tmp_path: Path) -> None:
        """Open should fail gracefully for missing files."""

        file_path = tmp_path / "missing.txt"
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Open(file_path))
        assert result.success is False
        assert "does not exist" in result.message

    def test_open_with_opener_failure(self, tmp_path: Path) -> None:
        """Open should propagate opener errors."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        opener = StubFileOpener(should_fail=True)
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Open(file_path))
        assert result.success is False
        assert "failed" in result.message


class TestActionHandlerText:
    """Tests for Text action handling."""

    def test_text_action_output(self, capsys) -> None:
        """Text actions should write to stdout."""

        handler = ActionHandler()
        result = handler.execute(Text("Hello, World!"))
        captured = capsys.readouterr()
        assert result.success is True
        assert "Hello, World!" in captured.out


class TestActionHandlerLink:
    """Tests for Link action handling."""

    def test_link_action(self, monkeypatch) -> None:
        """Link actions should open URLs via webbrowser."""

        opened_urls: list[str] = []

        def mock_open(url: str) -> None:
            opened_urls.append(url)

        monkeypatch.setattr("webbrowser.open", mock_open)
        handler = ActionHandler()
        result = handler.execute(Link("https://example.com"))
        assert result.success is True
        assert opened_urls == ["https://example.com"]


class TestActionHandlerCopy:
    """Tests for Copy action handling."""

    def test_copy_text(self) -> None:
        """Copy should delegate to clipboard implementation."""

        clipboard = StubClipboard()
        handler = ActionHandler(clipboard=clipboard)
        result = handler.execute(Copy("sample text"))
        assert result.success is True
        assert clipboard.last_text == "sample text"

    def test_copy_empty_text(self) -> None:
        """Copy should fail for empty text."""

        clipboard = StubClipboard()
        handler = ActionHandler(clipboard=clipboard)
        result = handler.execute(Copy(""))
        assert result.success is False
        assert "empty" in result.message

    def test_copy_with_clipboard_failure(self) -> None:
        """Copy should propagate clipboard errors."""

        clipboard = StubClipboard(should_fail=True)
        handler = ActionHandler(clipboard=clipboard)
        result = handler.execute(Copy("text"))
        assert result.success is False


class TestActionHandlerNotify:
    """Tests for Notify action handling."""

    def test_notify_with_title_only(self) -> None:
        """Notify should succeed with just a title."""

        notification = StubNotification()
        handler = ActionHandler(notification=notification)
        result = handler.execute(Notify("Title"))
        assert result.success is True
        assert notification.last_title == "Title"
        assert notification.last_message is None

    def test_notify_with_title_and_message(self) -> None:
        """Notify should handle title and message."""

        notification = StubNotification()
        handler = ActionHandler(notification=notification)
        result = handler.execute(Notify("Title", "Message"))
        assert result.success is True
        assert notification.last_title == "Title"
        assert notification.last_message == "Message"

    def test_notify_without_title(self) -> None:
        """Notify should fail when title is empty."""

        notification = StubNotification()
        handler = ActionHandler(notification=notification)
        result = handler.execute(Notify(""))
        assert result.success is False
        assert "required" in result.message

    def test_notify_with_notification_failure(self) -> None:
        """Notify should propagate notification errors."""

        notification = StubNotification(should_fail=True)
        handler = ActionHandler(notification=notification)
        result = handler.execute(Notify("Title"))
        assert result.success is False


class TestActionHandlerFolder:
    """Tests for Folder action handling."""

    def test_folder_existing_directory(self, tmp_path: Path) -> None:
        """Folder should succeed for existing directories."""

        folder_path = tmp_path / "folder"
        folder_path.mkdir()
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Folder(folder_path))
        assert result.success is True
        assert opener.opened_paths == [folder_path]

    def test_folder_missing_directory(self, tmp_path: Path) -> None:
        """Folder should fail gracefully for missing directories."""

        folder_path = tmp_path / "missing"
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Folder(folder_path))
        assert result.success is False
        assert "does not exist" in result.message

    def test_folder_not_a_directory(self, tmp_path: Path) -> None:
        """Folder should fail when target is not a directory."""

        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        opener = StubFileOpener()
        handler = ActionHandler(file_opener=opener)
        result = handler.execute(Folder(file_path))
        assert result.success is False
        assert "not a folder" in result.message


class TestActionHandlerNone:
    """Tests for NoneAction handling."""

    def test_none_action_no_reason(self) -> None:
        """NoneAction should succeed with default reason."""

        handler = ActionHandler()
        result = handler.execute(NoneAction())
        assert result.success is True
        assert "No action specified" in result.message

    def test_none_action_with_reason(self) -> None:
        """NoneAction should succeed with custom reason."""

        handler = ActionHandler()
        result = handler.execute(NoneAction("Task completed"))
        assert result.success is True
        assert result.message == "Task completed"
