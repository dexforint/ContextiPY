"""Unit tests for the context entry module."""

from unittest.mock import Mock

import pytest

from contextipy import oneshot_script
from contextipy.actions import Text
from contextipy.execution.context_entry import (
    ContextEntryCoordinator,
    ContextEntryError,
    main,
    parse_arguments,
)
from contextipy.execution.script_runner import ScriptInput, ScriptResult, ScriptRunner
from contextipy.execution.service_manager import ServiceManager


class TestParseArguments:
    """Tests for parse_arguments function."""

    def test_parse_basic_arguments(self) -> None:
        args = parse_arguments(["module:func"])
        assert args.script_id == "module:func"
        assert args.files == []
        assert args.params == "{}"
        assert args.answers == "{}"
        assert args.timeout is None
        assert args.dry_run is False

    def test_parse_with_files(self) -> None:
        args = parse_arguments(["module:func", "--files", "file1.txt", "file2.txt"])
        assert args.script_id == "module:func"
        assert args.files == ["file1.txt", "file2.txt"]

    def test_parse_with_params(self) -> None:
        args = parse_arguments(["module:func", "--params", '{"key": "value"}'])
        assert args.script_id == "module:func"
        assert args.params == '{"key": "value"}'

    def test_parse_with_answers(self) -> None:
        args = parse_arguments(["module:func", "--answers", '{"q1": "a1"}'])
        assert args.script_id == "module:func"
        assert args.answers == '{"q1": "a1"}'

    def test_parse_with_timeout(self) -> None:
        args = parse_arguments(["module:func", "--timeout", "30.0"])
        assert args.script_id == "module:func"
        assert args.timeout == 30.0

    def test_parse_with_dry_run(self) -> None:
        args = parse_arguments(["module:func", "--dry-run"])
        assert args.script_id == "module:func"
        assert args.dry_run is True


class TestContextEntryCoordinator:
    """Tests for ContextEntryCoordinator."""

    def test_init_with_defaults(self) -> None:
        coordinator = ContextEntryCoordinator()
        assert coordinator._script_runner is not None
        assert coordinator._service_manager is not None
        assert coordinator._action_handler is not None

    def test_init_with_custom_components(self) -> None:
        runner = Mock(spec=ScriptRunner)
        manager = Mock(spec=ServiceManager)
        
        coordinator = ContextEntryCoordinator(
            script_runner=runner,
            service_manager=manager,
        )
        
        assert coordinator._script_runner is runner
        assert coordinator._service_manager is manager

    def test_register_script(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> Text:
            return Text("Hello")

        metadata = my_script.__contextipy_metadata__
        
        coordinator = ContextEntryCoordinator()
        coordinator.register_script(metadata)
        
        assert "test_script" in coordinator._scripts

    def test_register_callable(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> Text:
            return Text("Hello")
        
        coordinator = ContextEntryCoordinator()
        result = coordinator.register_callable(my_script)
        
        assert "test_script" in coordinator._scripts
        assert result is my_script.__contextipy_metadata__

    def test_register_callable_no_metadata(self) -> None:
        def my_script() -> Text:
            return Text("Hello")
        
        coordinator = ContextEntryCoordinator()
        
        with pytest.raises(ContextEntryError, match="does not expose"):
            coordinator.register_callable(my_script)

    def test_execute_script_not_found(self) -> None:
        coordinator = ContextEntryCoordinator()
        result = coordinator.execute_script("unknown_script")
        
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_execute_script_success(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> Text:
            return Text("Hello")

        metadata = my_script.__contextipy_metadata__
        
        mock_runner = Mock(spec=ScriptRunner)
        mock_runner.run.return_value = ScriptResult(
            success=True,
            actions=(Text("Hello"),),
            stdout="",
            stderr="",
            exit_code=0,
            timed_out=False,
        )
        
        coordinator = ContextEntryCoordinator(script_runner=mock_runner)
        coordinator.register_script(metadata)
        
        result = coordinator.execute_script("test_script")
        
        assert result.success is True
        mock_runner.run.assert_called_once()

    def test_execute_script_failure(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script() -> Text:
            return Text("Hello")

        metadata = my_script.__contextipy_metadata__
        
        mock_runner = Mock(spec=ScriptRunner)
        mock_runner.run.return_value = ScriptResult(
            success=False,
            actions=(),
            stdout="",
            stderr="Error occurred",
            exit_code=1,
            timed_out=False,
            error_message="Test error",
        )
        
        coordinator = ContextEntryCoordinator(script_runner=mock_runner)
        coordinator.register_script(metadata)
        
        result = coordinator.execute_script("test_script")
        
        assert result.success is False

    def test_shutdown(self) -> None:
        mock_manager = Mock(spec=ServiceManager)
        coordinator = ContextEntryCoordinator(service_manager=mock_manager)
        
        coordinator.shutdown()
        
        mock_manager.shutdown.assert_called_once()


class TestMain:
    """Tests for main entry point."""

    def test_main_requires_colon_format(self) -> None:
        exit_code = main(["test_script"])
        assert exit_code == 1

    def test_main_with_invalid_params_json(self) -> None:
        exit_code = main(["module:func", "--params", "invalid json"])
        assert exit_code == 1

    def test_main_with_invalid_answers_json(self) -> None:
        exit_code = main(["module:func", "--answers", "invalid json"])
        assert exit_code == 1

    def test_main_with_params_not_dict(self) -> None:
        exit_code = main(["module:func", "--params", '"string"'])
        assert exit_code == 1

    def test_main_with_answers_not_dict(self) -> None:
        exit_code = main(["module:func", "--answers", '[1, 2, 3]'])
        assert exit_code == 1
