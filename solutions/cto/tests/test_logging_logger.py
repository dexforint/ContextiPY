"""Tests for the logging system capturing script execution metadata."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from contextipy import oneshot_script
from contextipy.actions import Copy, Notify, Text
from contextipy.execution.script_runner import ScriptInput, ScriptResult, ScriptRunner
from contextipy.logging.logger import (
    MAX_STDERR_LENGTH,
    MAX_STDOUT_LENGTH,
    ExecutionLog,
    ExecutionLogger,
)


class TestExecutionLog:
    """Tests for ExecutionLog dataclass."""

    def test_to_dict(self) -> None:
        from datetime import datetime

        log = ExecutionLog(
            run_id="test-run-id",
            script_id="test-script",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            status="success",
            exit_code=0,
            timed_out=False,
            error_message=None,
            actions_summary=[{"type": "text", "content": "<redacted>"}],
            stdout_excerpt="Hello World",
            stderr_excerpt="",
            input_payload={"parameters": {"key": "value"}},
        )

        result = log.to_dict()

        assert result["run_id"] == "test-run-id"
        assert result["script_id"] == "test-script"
        assert result["status"] == "success"
        assert result["exit_code"] == 0
        assert result["timed_out"] is False
        assert result["error_message"] is None
        assert result["actions_summary"] == [{"type": "text", "content": "<redacted>"}]
        assert result["stdout_excerpt"] == "Hello World"
        assert result["stderr_excerpt"] == ""
        assert result["input_payload"] == {"parameters": {"key": "value"}}


class TestExecutionLogger:
    """Tests for ExecutionLogger functionality."""

    def test_initialization(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        assert logger.path.exists()
        assert logger.path.name == "test_logs.db"

    def test_on_script_start_creates_active_run(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput(
            file_paths=(Path("/tmp/file1.txt"),),
            parameters={"key": "value"},
            ask_answers={"q1": "a1"},
        )

        logger.on_script_start("test-script", input_data)

        assert "test-script" in logger._active_runs
        run_id, start_time, stored_input = logger._active_runs["test-script"]
        assert isinstance(run_id, str)
        assert stored_input == input_data

    def test_logging_success(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput(parameters={"threshold": 10})

        logger.on_script_start("test-script", input_data)

        result = ScriptResult(
            success=True,
            actions=(Text("Hello"), Copy("World")),
            stdout="Script executed successfully",
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert log.script_id == "test-script"
        assert log.status == "success"
        assert log.exit_code == 0
        assert log.timed_out is False
        assert log.error_message is None
        assert log.stdout_excerpt == "Script executed successfully"
        assert log.stderr_excerpt == ""
        assert len(log.actions_summary) == 2
        assert log.actions_summary[0]["type"] == "text"
        assert log.actions_summary[1]["type"] == "copy"
        assert log.input_payload["parameters"] == {"threshold": 10}

    def test_logging_failure(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        result = ScriptResult(
            success=False,
            actions=(),
            stdout="",
            stderr="Error: File not found",
            exit_code=1,
            timed_out=False,
            error_message="Script subprocess failed",
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_runs_by_status("failure", limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert log.script_id == "test-script"
        assert log.status == "failure"
        assert log.exit_code == 1
        assert log.error_message == "Script subprocess failed"
        assert log.stderr_excerpt == "Error: File not found"

    def test_logging_timeout(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        result = ScriptResult(
            success=False,
            actions=(),
            stdout="Processing...",
            stderr="",
            exit_code=-1,
            timed_out=True,
            error_message="Script exceeded timeout of 10s",
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert log.timed_out is True
        assert "timeout" in log.error_message.lower()
        assert log.status == "failure"

    def test_on_script_error(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        error = RuntimeError("Unexpected error occurred")
        logger.on_script_error("test-script", error)

        logs = logger.get_runs_by_status("error", limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert log.script_id == "test-script"
        assert log.status == "error"
        assert "Unexpected error occurred" in log.error_message

    def test_truncate_long_stdout(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        long_stdout = "x" * (MAX_STDOUT_LENGTH + 500)
        result = ScriptResult(
            success=True,
            actions=(),
            stdout=long_stdout,
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert len(log.stdout_excerpt) == MAX_STDOUT_LENGTH + 3
        assert log.stdout_excerpt.endswith("...")

    def test_truncate_long_stderr(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        long_stderr = "y" * (MAX_STDERR_LENGTH + 500)
        result = ScriptResult(
            success=False,
            actions=(),
            stdout="",
            stderr=long_stderr,
            exit_code=1,
            timed_out=False,
            error_message="Error",
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert len(log.stderr_excerpt) == MAX_STDERR_LENGTH + 3
        assert log.stderr_excerpt.endswith("...")

    def test_get_runs_by_script(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")

        for i in range(3):
            input_data = ScriptInput()
            logger.on_script_start("script-a", input_data)
            result = ScriptResult(
                success=True,
                actions=(),
                stdout=f"Run {i}",
                stderr="",
                exit_code=0,
                timed_out=False,
                error_message=None,
            )
            logger.on_script_finish("script-a", result)

        for i in range(2):
            input_data = ScriptInput()
            logger.on_script_start("script-b", input_data)
            result = ScriptResult(
                success=True,
                actions=(),
                stdout=f"Run {i}",
                stderr="",
                exit_code=0,
                timed_out=False,
                error_message=None,
            )
            logger.on_script_finish("script-b", result)

        logs_a = logger.get_runs_by_script("script-a", limit=10)
        assert len(logs_a) == 3
        assert all(log.script_id == "script-a" for log in logs_a)

        logs_b = logger.get_runs_by_script("script-b", limit=10)
        assert len(logs_b) == 2
        assert all(log.script_id == "script-b" for log in logs_b)

    def test_get_run_by_id(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)
        result = ScriptResult(
            success=True,
            actions=(Text("Hello"),),
            stdout="Output",
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )
        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=1)
        run_id = logs[0].run_id

        log = logger.get_run_by_id(run_id)
        assert log is not None
        assert log.run_id == run_id
        assert log.script_id == "test-script"

        non_existent_log = logger.get_run_by_id("non-existent-id")
        assert non_existent_log is None

    def test_rehydrate_input(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        original_input = ScriptInput(
            file_paths=(Path("/tmp/file1.txt"), Path("/tmp/file2.txt")),
            parameters={"threshold": 42, "enabled": True},
            ask_answers={"question1": "answer1"},
        )

        logger.on_script_start("test-script", original_input)
        result = ScriptResult(
            success=True,
            actions=(),
            stdout="",
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )
        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=1)
        run_id = logs[0].run_id

        rehydrated_input = logger.rehydrate_input(run_id)

        assert rehydrated_input.file_paths == original_input.file_paths
        assert rehydrated_input.parameters == original_input.parameters
        assert rehydrated_input.ask_answers == original_input.ask_answers

    def test_rehydrate_input_not_found(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")

        with pytest.raises(KeyError, match="Run 'non-existent-id' not found"):
            logger.rehydrate_input("non-existent-id")

    def test_integration_with_script_runner(self, tmp_path: Path) -> None:
        @oneshot_script(
            script_id="integration-test",
            title="Integration Test",
            description="Test integration with script runner",
        )
        def test_script(threshold: int = 10) -> Text:
            return Text(f"Threshold is {threshold}")

        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        runner = ScriptRunner(event_hook=logger)

        metadata = test_script.__contextipy_metadata__
        input_data = ScriptInput(parameters={"threshold": 42})

        with patch("contextipy.execution.script_runner.subprocess.run") as mock_run:
            import base64
            import pickle

            actions = [Text("Threshold is 42")]
            encoded = base64.b64encode(pickle.dumps(actions)).decode("ascii")

            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout = encoded.encode("utf-8")
            mock_process.stderr = b""
            mock_run.return_value = mock_process

            result = runner.run(metadata, input_data=input_data)

        assert result.success is True

        logs = logger.get_recent_runs(limit=10)
        assert len(logs) == 1

        log = logs[0]
        assert log.script_id == "integration-test"
        assert log.status == "success"
        assert log.input_payload["parameters"]["threshold"] == 42

    def test_actions_serialization(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")
        input_data = ScriptInput()

        logger.on_script_start("test-script", input_data)

        actions = (
            Text("Hello World"),
            Copy("clipboard content"),
            Notify("Notification Title", "Notification Message"),
        )

        result = ScriptResult(
            success=True,
            actions=actions,
            stdout="",
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=1)
        log = logs[0]

        assert len(log.actions_summary) == 3
        assert log.actions_summary[0]["type"] == "text"
        assert log.actions_summary[1]["type"] == "copy"
        assert log.actions_summary[2]["type"] == "notify"

        assert len(log.actions) == 3
        assert isinstance(log.actions[0], Text)
        assert isinstance(log.actions[1], Copy)
        assert isinstance(log.actions[2], Notify)
        assert log.actions[0].content == "Hello World"
        assert log.actions[1].text == "clipboard content"
        assert log.actions[2].title == "Notification Title"

    def test_repeat_payload_serialization(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")

        original_actions = (
            Text("Result 1"),
            Copy("Data to copy"),
            Notify("Done", "Process completed"),
        )

        input_data = ScriptInput(
            file_paths=(Path("/tmp/input.txt"),),
            parameters={"key": "value", "count": 5},
            ask_answers={"confirm": "yes"},
        )

        logger.on_script_start("test-script", input_data)

        result = ScriptResult(
            success=True,
            actions=original_actions,
            stdout="Script output",
            stderr="",
            exit_code=0,
            timed_out=False,
            error_message=None,
        )

        logger.on_script_finish("test-script", result)

        logs = logger.get_recent_runs(limit=1)
        run_id = logs[0].run_id

        rehydrated_input = logger.rehydrate_input(run_id)
        assert rehydrated_input.file_paths == input_data.file_paths
        assert rehydrated_input.parameters == input_data.parameters
        assert rehydrated_input.ask_answers == input_data.ask_answers

        log = logger.get_run_by_id(run_id)
        assert log is not None
        assert len(log.actions) == 3
        assert isinstance(log.actions[0], Text)
        assert log.actions[0].content == "Result 1"
        assert isinstance(log.actions[1], Copy)
        assert log.actions[1].text == "Data to copy"
        assert isinstance(log.actions[2], Notify)
        assert log.actions[2].title == "Done"
        assert log.actions[2].message == "Process completed"

    def test_multiple_runs_ordering(self, tmp_path: Path) -> None:
        logger = ExecutionLogger(path=tmp_path / "test_logs.db")

        for i in range(5):
            input_data = ScriptInput()
            logger.on_script_start(f"script-{i}", input_data)
            result = ScriptResult(
                success=True,
                actions=(),
                stdout=f"Run {i}",
                stderr="",
                exit_code=0,
                timed_out=False,
                error_message=None,
            )
            logger.on_script_finish(f"script-{i}", result)

        logs = logger.get_recent_runs(limit=3)
        assert len(logs) == 3
        assert logs[0].script_id == "script-4"
        assert logs[1].script_id == "script-3"
        assert logs[2].script_id == "script-2"
