"""Context menu entry point and coordination utilities."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from contextipy.actions import Action
from contextipy.core.decorators import get_metadata
from contextipy.core.metadata import (
    OneshotScriptMetadata,
    ServiceMetadata,
    ServiceScriptMetadata,
)
from contextipy.execution.action_handler import ActionHandler, ActionResult
from contextipy.execution.script_runner import ScriptInput, ScriptResult, ScriptRunner
from contextipy.execution.service_manager import ServiceManager

ScriptMetadataType = OneshotScriptMetadata | ServiceScriptMetadata


class ContextEntryError(RuntimeError):
    """Raised when context entry coordination fails."""


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for context entry invocation."""

    parser = argparse.ArgumentParser(
        prog="contextipy-context",
        description="Execute Contextipy scripts via the context menu",
    )
    parser.add_argument("script_id", help="Script identifier or module:qualname reference")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Selected file paths to supply to the script",
    )
    parser.add_argument(
        "--params",
        type=str,
        default="{}",
        help="JSON encoded parameters to pass to the script",
    )
    parser.add_argument(
        "--answers",
        type=str,
        default="{}",
        help="JSON encoded Ask answers to supply to the script",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional override for the script timeout in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and log actions without executing them",
    )
    return parser.parse_args(args)


class ContextEntryCoordinator:
    """Coordinates execution of registered scripts from the context menu."""

    def __init__(
        self,
        *,
        script_runner: ScriptRunner | None = None,
        service_manager: ServiceManager | None = None,
        action_handler: ActionHandler | None = None,
    ) -> None:
        self._script_runner = script_runner or ScriptRunner()
        self._service_manager = service_manager or ServiceManager()
        self._action_handler = action_handler or ActionHandler()
        self._scripts: dict[str, ScriptMetadataType] = {}
        self._services: dict[str, ServiceMetadata] = {}

    def register_script(self, metadata: ScriptMetadataType) -> None:
        """Register script *metadata* with the coordinator."""

        self._scripts[metadata.id] = metadata

    def register_service(self, metadata: ServiceMetadata) -> None:
        """Register service *metadata* and ensure the manager knows how to start it."""

        self._services[metadata.id] = metadata
        factory = _make_service_factory(metadata)
        try:
            self._service_manager.register_service(metadata.id, factory)
        except ValueError:
            # It is acceptable for the service to already be registered.
            pass

    def register_metadata(
        self, metadata: ServiceMetadata | ScriptMetadataType
    ) -> ServiceMetadata | ScriptMetadataType:
        """Register metadata regardless of its specific type."""

        if isinstance(metadata, ServiceMetadata):
            self.register_service(metadata)
        else:
            self.register_script(metadata)
        return metadata

    def register_callable(self, target: Any) -> ServiceMetadata | ScriptMetadataType:
        """Register the metadata attached to *target* via decorators."""

        metadata = get_metadata(target)
        if metadata is None:
            raise ContextEntryError("Target does not expose Contextipy metadata")
        return self.register_metadata(metadata)

    def register_module_target(self, module: str, qualname: str) -> ServiceMetadata | ScriptMetadataType:
        """Import *module* and register the object described by *qualname*."""

        obj = _resolve_attribute(module, qualname)
        return self.register_callable(obj)

    def execute_script(
        self,
        script_id: str,
        *,
        file_paths: Sequence[Path] | None = None,
        parameters: Mapping[str, Any] | None = None,
        ask_answers: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ActionResult:
        """Execute the script identified by *script_id*."""

        metadata = self._scripts.get(script_id)
        if metadata is None:
            return ActionResult(success=False, message=f"Script not found: {script_id}")

        selection = tuple(file_paths or ())
        params = dict(parameters or {})
        answers = dict(ask_answers or {})

        if isinstance(metadata, ServiceScriptMetadata):
            if metadata.service_id not in self._services:
                return ActionResult(
                    success=False,
                    message=f"Required service not registered: {metadata.service_id}",
                )
            if not self._service_manager.ensure_service_running(metadata.service_id):
                return ActionResult(
                    success=False,
                    message=f"Failed to start required service: {metadata.service_id}",
                )

        input_payload = ScriptInput(
            file_paths=selection,
            parameters=params,
            ask_answers=answers,
        )
        result = self._script_runner.run(
            metadata,
            input_data=input_payload,
            timeout=timeout,
        )

        if not result.success:
            message = result.error_message or result.stderr or "Script execution failed"
            return ActionResult(success=False, message=message)

        return self._execute_actions(metadata.id, result)

    def shutdown(self) -> None:
        """Shutdown the coordinator and underlying services."""

        self._service_manager.shutdown()

    def _execute_actions(self, script_id: str, result: ScriptResult) -> ActionResult:
        actions = result.actions
        if not actions:
            return ActionResult(success=True, message=f"Script {script_id} completed (no actions)")

        action_results: list[ActionResult] = []
        overall_success = True
        for action in actions:
            action_result = self._action_handler.execute(action)
            action_results.append(action_result)
            if not action_result.success:
                overall_success = False

        messages = [res.message for res in action_results if res.message]
        message = "; ".join(messages) if messages else None
        if overall_success:
            return ActionResult(success=True, message=message)
        return ActionResult(success=False, message=message or "One or more actions failed")


def _make_service_factory(metadata: ServiceMetadata) -> Any:
    target = metadata.target
    if inspect.isclass(target):
        return target

    def factory() -> Any:
        return target()

    return factory


def _resolve_attribute(module: str, qualname: str) -> Any:
    obj = importlib.import_module(module)
    current: Any = obj
    for part in qualname.split("."):
        if not hasattr(current, part):
            raise ContextEntryError(f"Unable to resolve attribute '{part}' in {module}")
        current = getattr(current, part)
    return current


def main(args: list[str] | None = None) -> int:
    """CLI entry point invoked from the context menu."""

    parsed = parse_arguments(args)

    try:
        parameters = json.loads(parsed.params)
        if not isinstance(parameters, dict):
            raise ValueError("--params must encode a JSON object")
    except json.JSONDecodeError as exc:
        print(f"Error parsing --params: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        ask_answers = json.loads(parsed.answers)
        if not isinstance(ask_answers, dict):
            raise ValueError("--answers must encode a JSON object")
    except json.JSONDecodeError as exc:
        print(f"Error parsing --answers: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    file_paths = [Path(path) for path in parsed.files]

    if ":" not in parsed.script_id:
        print("Script identifier must be in 'module:qualname' format", file=sys.stderr)
        return 1

    module_name, _, qualname = parsed.script_id.partition(":")

    coordinator = ContextEntryCoordinator(
        action_handler=ActionHandler(dry_run=parsed.dry_run)
    )

    try:
        metadata = coordinator.register_module_target(module_name, qualname)
        script_id = metadata.id if not isinstance(metadata, ServiceMetadata) else None
        if script_id is None:
            print("Provided identifier refers to a service, not a script", file=sys.stderr)
            return 1
    except ContextEntryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        result = coordinator.execute_script(
            script_id,
            file_paths=file_paths,
            parameters=parameters,
            ask_answers=ask_answers,
            timeout=parsed.timeout,
        )
        if result.message:
            print(result.message)
        return 0 if result.success else 1
    finally:
        coordinator.shutdown()


__all__ = [
    "ContextEntryCoordinator",
    "ContextEntryError",
    "parse_arguments",
    "main",
]
