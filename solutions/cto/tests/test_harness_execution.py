"""Test harness for execution flows with fixture-based isolation."""

from __future__ import annotations

import pickle
import subprocess
from base64 import b64encode
from pathlib import Path
from unittest.mock import Mock

import pytest

from contextipy import oneshot_script, service, service_script
from contextipy.actions import Text
from contextipy.execution.script_runner import ScriptInput, ScriptResult, ScriptRunner


@pytest.mark.usefixtures("isolated_registry")
class TestExecutionHappyPath:
    """Test successful execution flows with subprocess mocking."""

    def test_oneshot_script_execution_with_mock_subprocess(
        self, mock_subprocess: Mock
    ) -> None:
        """Test that oneshot scripts execute correctly with mocked subprocess."""

        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def sample_script() -> Text:
            return Text("Hello World")

        metadata = sample_script.__contextipy_metadata__
        encoded_output = b64encode(pickle.dumps([Text("Hello World")])).decode("ascii")
        mock_subprocess.return_value.stdout = encoded_output.encode("utf-8")
        mock_subprocess.return_value.returncode = 0

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is True
        assert len(result.actions) == 1
        assert isinstance(result.actions[0], Text)
        assert result.actions[0].content == "Hello World"
        assert result.exit_code == 0
        assert result.timed_out is False

    def test_oneshot_script_with_parameters(self, mock_subprocess: Mock) -> None:
        """Test script execution with input parameters."""

        @oneshot_script(
            script_id="param_script",
            title="Parametrized Script",
            description="Script with parameters",
        )
        def param_script(name: str = "World") -> Text:
            return Text(f"Hello {name}")

        metadata = param_script.__contextipy_metadata__
        encoded_output = b64encode(pickle.dumps([Text("Hello Alice")])).decode("ascii")
        mock_subprocess.return_value.stdout = encoded_output.encode("utf-8")
        mock_subprocess.return_value.returncode = 0

        runner = ScriptRunner()
        input_data = ScriptInput(parameters={"name": "Alice"})
        result = runner.run(metadata, input_data=input_data)

        assert result.success is True
        assert len(result.actions) == 1
        assert result.actions[0].content == "Hello Alice"

    def test_script_execution_timeout(self, mock_subprocess: Mock) -> None:
        """Test that script timeouts are handled correctly."""

        @oneshot_script(
            script_id="slow_script",
            title="Slow Script",
            description="A slow script",
            timeout=1.0,
        )
        def slow_script() -> Text:
            return Text("Done")

        metadata = slow_script.__contextipy_metadata__
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["python"], timeout=1.0, output=b"partial", stderr=b""
        )

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is False
        assert result.timed_out is True
        assert "timeout" in result.error_message.lower()
        assert result.exit_code == -1

    def test_script_execution_failure(self, mock_subprocess: Mock) -> None:
        """Test that script failures are captured properly."""

        @oneshot_script(
            script_id="failing_script",
            title="Failing Script",
            description="A script that fails",
        )
        def failing_script() -> Text:
            return Text("Should not reach")

        metadata = failing_script.__contextipy_metadata__
        mock_subprocess.return_value.stdout = b""
        mock_subprocess.return_value.stderr = b"Error: Something went wrong"
        mock_subprocess.return_value.returncode = 1

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is False
        assert result.exit_code == 1
        assert "Something went wrong" in result.stderr


@pytest.mark.usefixtures("isolated_registry")
class TestServiceExecutionFlow:
    """Test service and service_script execution."""

    def test_service_registration(self) -> None:
        """Test that services register correctly."""

        @service(
            service_id="test_service",
            title="Test Service",
            description="A test service",
        )
        def test_service() -> None:
            pass

        metadata = test_service.__contextipy_metadata__
        assert metadata.id == "test_service"
        assert metadata.title == "Test Service"

    def test_service_script_registration(self) -> None:
        """Test that service scripts register and link to services."""

        @service(
            service_id="linked_service",
            title="Linked Service",
            description="Service with scripts",
        )
        def linked_service() -> None:
            pass

        @service_script(
            script_id="control_script",
            service_id="linked_service",
            title="Control Script",
            description="Controls the service",
        )
        def control_script() -> None:
            pass

        service_metadata = linked_service.__contextipy_metadata__
        script_metadata = control_script.__contextipy_metadata__

        assert script_metadata.service_id == "linked_service"
        assert len(service_metadata.service_scripts) == 1
        assert service_metadata.service_scripts[0].id == "control_script"

    def test_service_script_execution(self, mock_subprocess: Mock) -> None:
        """Test that service scripts can be executed."""

        @service(
            service_id="exec_service",
            title="Executable Service",
            description="Service with executable scripts",
        )
        def exec_service() -> None:
            pass

        @service_script(
            script_id="start_script",
            service_id="exec_service",
            title="Start Script",
            description="Starts the service",
        )
        def start_script() -> Text:
            return Text("Service started")

        metadata = start_script.__contextipy_metadata__
        encoded_output = b64encode(pickle.dumps([Text("Service started")])).decode("ascii")
        mock_subprocess.return_value.stdout = encoded_output.encode("utf-8")
        mock_subprocess.return_value.returncode = 0

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is True
        assert len(result.actions) == 1
        assert result.actions[0].content == "Service started"


@pytest.mark.usefixtures("isolated_registry")
class TestScriptInputSerialization:
    """Test ScriptInput serialization and deserialization."""

    def test_script_input_empty(self) -> None:
        """Test empty ScriptInput serialization."""
        input_data = ScriptInput()
        json_str = input_data.to_json()
        restored = ScriptInput.from_json(json_str)

        assert restored.file_paths == ()
        assert restored.parameters == {}
        assert restored.ask_answers == {}

    def test_script_input_with_data(self, tmp_path: Path) -> None:
        """Test ScriptInput with data serialization."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        input_data = ScriptInput(
            file_paths=(file1, file2),
            parameters={"count": 5, "enabled": True},
            ask_answers={"question1": "answer1"},
        )

        json_str = input_data.to_json()
        restored = ScriptInput.from_json(json_str)

        assert len(restored.file_paths) == 2
        assert restored.file_paths[0] == file1
        assert restored.file_paths[1] == file2
        assert restored.parameters == {"count": 5, "enabled": True}
        assert restored.ask_answers == {"question1": "answer1"}


@pytest.mark.usefixtures("isolated_registry")
class TestEventHooks:
    """Test script execution event hooks."""

    def test_event_hook_on_success(self, mock_subprocess: Mock) -> None:
        """Test that event hooks are called on successful execution."""

        @oneshot_script(
            script_id="hook_test",
            title="Hook Test",
            description="Test event hooks",
        )
        def hook_test() -> Text:
            return Text("Success")

        events: list[str] = []

        class TestHook:
            def on_script_start(self, script_id: str, input_data: ScriptInput) -> None:
                events.append(f"start:{script_id}")

            def on_script_finish(self, script_id: str, result: ScriptResult) -> None:
                events.append(f"finish:{script_id}:{result.success}")

            def on_script_error(self, script_id: str, error: Exception) -> None:
                events.append(f"error:{script_id}")

        metadata = hook_test.__contextipy_metadata__
        encoded_output = b64encode(pickle.dumps([Text("Success")])).decode("ascii")
        mock_subprocess.return_value.stdout = encoded_output.encode("utf-8")
        mock_subprocess.return_value.returncode = 0

        runner = ScriptRunner(event_hook=TestHook())
        result = runner.run(metadata)

        assert result.success is True
        assert events == ["start:hook_test", "finish:hook_test:True"]

    def test_event_hook_on_failure(self, mock_subprocess: Mock) -> None:
        """Test that event hooks are called on failed execution."""

        @oneshot_script(
            script_id="fail_hook",
            title="Fail Hook Test",
            description="Test event hooks on failure",
        )
        def fail_hook() -> Text:
            return Text("Should not reach")

        events: list[str] = []

        class TestHook:
            def on_script_start(self, script_id: str, input_data: ScriptInput) -> None:
                events.append("start")

            def on_script_finish(self, script_id: str, result: ScriptResult) -> None:
                events.append(f"finish:{result.success}")

            def on_script_error(self, script_id: str, error: Exception) -> None:
                events.append("error")

        metadata = fail_hook.__contextipy_metadata__
        mock_subprocess.return_value.stdout = b""
        mock_subprocess.return_value.stderr = b"Error occurred"
        mock_subprocess.return_value.returncode = 1

        runner = ScriptRunner(event_hook=TestHook())
        result = runner.run(metadata)

        assert result.success is False
        assert events == ["start", "finish:False"]


@pytest.mark.usefixtures("isolated_registry")
class TestCustomPythonExecutable:
    """Test ScriptRunner with custom Python executable."""

    def test_custom_python_executable(self, mock_subprocess: Mock) -> None:
        """Test that custom Python executable is used."""

        @oneshot_script(
            script_id="custom_python",
            title="Custom Python",
            description="Test custom Python executable",
        )
        def custom_python() -> Text:
            return Text("Done")

        metadata = custom_python.__contextipy_metadata__
        encoded_output = b64encode(pickle.dumps([Text("Done")])).decode("ascii")
        mock_subprocess.return_value.stdout = encoded_output.encode("utf-8")
        mock_subprocess.return_value.returncode = 0

        runner = ScriptRunner(python_executable="/custom/bin/python")
        runner.run(metadata)

        # Verify subprocess.run was called with custom Python
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0][0] == "/custom/bin/python"
