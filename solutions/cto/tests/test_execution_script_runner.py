"""Unit tests for the script runner module."""

import pickle
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from contextipy import oneshot_script
from contextipy.actions import Copy, Text
from contextipy.execution.script_runner import (
    DefaultEventHook,
    ScriptEventHook,
    ScriptInput,
    ScriptResult,
    ScriptRunner,
    _decode_actions_payload,
    _normalise_actions,
    _resolve_callable,
    create_script_runner,
)


class TestScriptInput:
    """Tests for ScriptInput serialisation."""

    def test_to_json_empty(self) -> None:
        input_data = ScriptInput()
        json_str = input_data.to_json()
        assert json_str == '{"file_paths": [], "parameters": {}, "ask_answers": {}}'

    def test_to_json_with_data(self) -> None:
        input_data = ScriptInput(
            file_paths=(Path("/tmp/file.txt"), Path("/tmp/file2.txt")),
            parameters={"key": "value", "count": 42},
            ask_answers={"question1": "answer1"},
        )
        json_str = input_data.to_json()
        assert '"/tmp/file.txt"' in json_str
        assert '"/tmp/file2.txt"' in json_str
        assert '"key": "value"' in json_str
        assert '"count": 42' in json_str
        assert '"question1": "answer1"' in json_str

    def test_from_json_empty_string(self) -> None:
        input_data = ScriptInput.from_json("")
        assert input_data.file_paths == ()
        assert input_data.parameters == {}
        assert input_data.ask_answers == {}

    def test_from_json_with_data(self) -> None:
        json_str = (
            '{"file_paths": ["/tmp/file.txt"], '
            '"parameters": {"key": "value"}, '
            '"ask_answers": {"q1": "a1"}}'
        )
        input_data = ScriptInput.from_json(json_str)
        assert len(input_data.file_paths) == 1
        assert input_data.file_paths[0] == Path("/tmp/file.txt")
        assert input_data.parameters == {"key": "value"}
        assert input_data.ask_answers == {"q1": "a1"}

    def test_round_trip(self) -> None:
        original = ScriptInput(
            file_paths=(Path("/tmp/test.txt"),),
            parameters={"x": 10},
            ask_answers={"ask_key": "ask_value"},
        )
        json_str = original.to_json()
        restored = ScriptInput.from_json(json_str)
        assert restored.file_paths == original.file_paths
        assert restored.parameters == original.parameters
        assert restored.ask_answers == original.ask_answers


class TestDefaultEventHook:
    """Tests for DefaultEventHook."""

    def test_on_script_start(self) -> None:
        hook = DefaultEventHook()
        input_data = ScriptInput()
        result = hook.on_script_start("test_script", input_data)
        assert result is None

    def test_on_script_finish(self) -> None:
        hook = DefaultEventHook()
        result_obj = ScriptResult(
            success=True, actions=(), stdout="", stderr="", exit_code=0, timed_out=False
        )
        result = hook.on_script_finish("test_script", result_obj)
        assert result is None

    def test_on_script_error(self) -> None:
        hook = DefaultEventHook()
        result = hook.on_script_error("test_script", Exception("test error"))
        assert result is None


class TestScriptRunner:
    """Tests for ScriptRunner."""

    def test_init_with_defaults(self) -> None:
        runner = ScriptRunner()
        assert runner._event_hook is not None
        assert runner._python is not None

    def test_init_with_custom_event_hook(self) -> None:
        mock_hook = Mock(spec=ScriptEventHook)
        runner = ScriptRunner(event_hook=mock_hook)
        assert runner._event_hook is mock_hook

    def test_init_with_custom_python(self) -> None:
        runner = ScriptRunner(python_executable="/custom/python")
        assert runner._python == "/custom/python"

    @patch("contextipy.execution.script_runner.subprocess.run")
    def test_run_success(self, mock_run: MagicMock) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> Text:
            return Text("Hello")

        metadata = my_script.__contextipy_metadata__
        encoded_payload = pickle.dumps([Text("Hello")])
        import base64

        encoded = base64.b64encode(encoded_payload).decode("ascii")

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = encoded.encode("utf-8")
        mock_process.stderr = b""
        mock_run.return_value = mock_process

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is True
        assert len(result.actions) == 1
        assert isinstance(result.actions[0], Text)
        assert result.exit_code == 0
        assert result.timed_out is False

    @patch("contextipy.execution.script_runner.subprocess.run")
    def test_run_with_timeout(self, mock_run: MagicMock) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
            timeout=5.0,
        )
        def my_script() -> None:
            return None

        metadata = my_script.__contextipy_metadata__

        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python"], timeout=5.0)

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is False
        assert result.timed_out is True
        assert "timeout" in result.error_message.lower()

    @patch("contextipy.execution.script_runner.subprocess.run")
    def test_run_with_custom_timeout(self, mock_run: MagicMock) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> None:
            return None

        metadata = my_script.__contextipy_metadata__

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = b""
        mock_process.stderr = b""
        mock_run.return_value = mock_process

        runner = ScriptRunner()
        runner.run(metadata, timeout=10.0)

        assert mock_run.call_args.kwargs["timeout"] == 10.0

    @patch("contextipy.execution.script_runner.subprocess.run")
    def test_run_nonzero_exit_code(self, mock_run: MagicMock) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> None:
            return None

        metadata = my_script.__contextipy_metadata__

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stdout = b""
        mock_process.stderr = b"Error occurred"
        mock_run.return_value = mock_process

        runner = ScriptRunner()
        result = runner.run(metadata)

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Error occurred"

    def test_run_calls_event_hooks(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> None:
            return None

        metadata = my_script.__contextipy_metadata__
        mock_hook = Mock(spec=ScriptEventHook)

        with patch("contextipy.execution.script_runner.subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout = b""
            mock_process.stderr = b""
            mock_run.return_value = mock_process

            runner = ScriptRunner(event_hook=mock_hook)
            runner.run(metadata)

            assert mock_hook.on_script_start.called
            assert mock_hook.on_script_finish.called


class TestDecodeActionsPayload:
    """Tests for _decode_actions_payload."""

    def test_empty_payload(self) -> None:
        actions = _decode_actions_payload(b"")
        assert actions == []

    def test_valid_payload(self) -> None:
        import base64

        actions_list = [Text("Hello"), Copy("World")]
        encoded = base64.b64encode(pickle.dumps(actions_list))
        decoded = _decode_actions_payload(encoded)
        assert len(decoded) == 2
        assert isinstance(decoded[0], Text)
        assert isinstance(decoded[1], Copy)

    def test_invalid_payload_not_list(self) -> None:
        import base64

        payload = base64.b64encode(pickle.dumps("not a list"))
        with pytest.raises(TypeError, match="not a list"):
            _decode_actions_payload(payload)

    def test_invalid_payload_wrong_type(self) -> None:
        import base64

        payload = base64.b64encode(pickle.dumps([Text("Hello"), "invalid"]))
        with pytest.raises(TypeError, match="non-action value"):
            _decode_actions_payload(payload)


class TestResolveCallable:
    """Tests for _resolve_callable."""

    def test_resolve_function(self) -> None:
        target = _resolve_callable("contextipy.actions", "serialize_action_for_log")
        from contextipy.actions import serialize_action_for_log

        assert target is serialize_action_for_log

    def test_resolve_class(self) -> None:
        target = _resolve_callable("contextipy.actions", "Open")
        from contextipy.actions import Open

        assert target is Open


class TestNormaliseActions:
    """Tests for _normalise_actions."""

    def test_none_value(self) -> None:
        actions = _normalise_actions(None)
        assert actions == []

    def test_single_action(self) -> None:
        text = Text("Hello")
        actions = _normalise_actions(text)
        assert actions == [text]

    def test_list_of_actions(self) -> None:
        text = Text("Hello")
        copy = Copy("World")
        actions = _normalise_actions([text, copy])
        assert actions == [text, copy]

    def test_tuple_of_actions(self) -> None:
        text = Text("Hello")
        actions = _normalise_actions((text,))
        assert actions == [text]

    def test_unsupported_action_type(self) -> None:
        with pytest.raises(TypeError, match="Unsupported action type"):
            _normalise_actions([Text("Hello"), "invalid"])

    def test_unexpected_result_type(self) -> None:
        with pytest.raises(TypeError, match="Unexpected script result type"):
            _normalise_actions(42)


class TestCreateScriptRunner:
    """Tests for create_script_runner factory function."""

    def test_creates_runner(self) -> None:
        runner = create_script_runner()
        assert isinstance(runner, ScriptRunner)

    def test_passes_event_hook(self) -> None:
        mock_hook = Mock(spec=ScriptEventHook)
        runner = create_script_runner(event_hook=mock_hook)
        assert runner._event_hook is mock_hook
