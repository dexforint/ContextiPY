"""Isolated execution of Contextipy scripts in subprocesses.

This module provides the :class:`ScriptRunner` which launches registered
Contextipy scripts inside dedicated Python subprocesses. Parameters, selected
files, and Ask answers are serialised and passed to the worker process via
stdin. The worker imports the target callable, executes it, pickles any returned
actions, and emits the payload over stdout. The parent process enforces
timeouts, captures stdout/stderr, and normalises the results for further
handling by the UI.
"""

from __future__ import annotations

import argparse
import base64
import importlib
import inspect
import json
import pickle
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence

from contextipy.actions import (
    Action,
    Copy,
    Folder,
    Link,
    NoneAction,
    Notify,
    Open,
    Text,
)
from contextipy.core.metadata import OneshotScriptMetadata, ServiceScriptMetadata

_ACTION_TYPES = (Open, Text, Link, Copy, Notify, Folder, NoneAction)


@dataclass(frozen=True, slots=True)
class ScriptInput:
    """Input payload supplied to script executions."""

    file_paths: tuple[Path, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    ask_answers: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialise the input payload into JSON."""

        return json.dumps(
            {
                "file_paths": [str(path) for path in self.file_paths],
                "parameters": self.parameters,
                "ask_answers": self.ask_answers,
            }
        )

    @classmethod
    def from_json(cls, data: str) -> ScriptInput:
        """Deserialise *data* into a :class:`ScriptInput` instance."""

        if not data.strip():
            return cls()
        payload = json.loads(data)
        file_paths = tuple(Path(path) for path in payload.get("file_paths", ()))
        parameters = dict(payload.get("parameters", {}))
        ask_answers = dict(payload.get("ask_answers", {}))
        return cls(file_paths=file_paths, parameters=parameters, ask_answers=ask_answers)


@dataclass(frozen=True, slots=True)
class ScriptResult:
    """Outcome of executing a script."""

    success: bool
    actions: tuple[Action, ...]
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    error_message: str | None = None


class ScriptEventHook(Protocol):
    """Protocol for receiving script execution events."""

    def on_script_start(self, script_id: str, input_data: ScriptInput) -> None:
        """Invoked just before a script execution begins."""
        ...

    def on_script_finish(self, script_id: str, result: ScriptResult) -> None:
        """Invoked when a script execution completes successfully."""
        ...

    def on_script_error(self, script_id: str, error: Exception) -> None:
        """Invoked when an unexpected error occurs during execution."""
        ...


class DefaultEventHook:
    """Default event hook that performs no additional processing."""

    def on_script_start(self, script_id: str, input_data: ScriptInput) -> None:
        return None

    def on_script_finish(self, script_id: str, result: ScriptResult) -> None:
        return None

    def on_script_error(self, script_id: str, error: Exception) -> None:
        return None


ScriptMetadata = OneshotScriptMetadata | ServiceScriptMetadata


class ScriptRunner:
    """Launch Contextipy scripts in isolated subprocesses."""

    def __init__(
        self,
        *,
        event_hook: ScriptEventHook | None = None,
        python_executable: str | None = None,
    ) -> None:
        self._event_hook = event_hook or DefaultEventHook()
        self._python = python_executable or sys.executable

    def run(
        self,
        metadata: ScriptMetadata,
        *,
        input_data: ScriptInput | None = None,
        timeout: float | None = None,
    ) -> ScriptResult:
        """Execute *metadata* in a subprocess and return the result."""

        script_id = metadata.id
        payload = input_data or ScriptInput()
        self._event_hook.on_script_start(script_id, payload)

        effective_timeout = timeout if timeout is not None else metadata.timeout

        command = [
            self._python,
            "-m",
            "contextipy.execution.script_runner",
            "--module",
            metadata.target.__module__,
            "--qualname",
            metadata.target.__qualname__,
        ]

        try:
            completed = subprocess.run(
                command,
                input=payload.to_json().encode("utf-8"),
                capture_output=True,
                timeout=effective_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_text = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
            stderr_text = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            result = ScriptResult(
                success=False,
                actions=(),
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=-1,
                timed_out=True,
                error_message=f"Script exceeded timeout of {effective_timeout}s",
            )
            self._event_hook.on_script_finish(script_id, result)
            return result
        except Exception as exc:  # pragma: no cover - defensive guard
            self._event_hook.on_script_error(script_id, exc)
            return ScriptResult(
                success=False,
                actions=(),
                stdout="",
                stderr="",
                exit_code=-1,
                timed_out=False,
                error_message=f"Failed to launch script subprocess: {exc}",
            )

        stdout_text = completed.stdout.decode("utf-8", errors="replace")
        stderr_text = completed.stderr.decode("utf-8", errors="replace")

        if completed.returncode != 0:
            result = ScriptResult(
                success=False,
                actions=(),
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=completed.returncode,
                timed_out=False,
                error_message=stderr_text or "Script subprocess failed",
            )
            self._event_hook.on_script_finish(script_id, result)
            return result

        try:
            actions = _decode_actions_payload(completed.stdout)
        except Exception as exc:  # pragma: no cover - defensive guard
            result = ScriptResult(
                success=False,
                actions=(),
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=completed.returncode,
                timed_out=False,
                error_message=f"Failed to decode script actions: {exc}",
            )
            self._event_hook.on_script_finish(script_id, result)
            return result

        result = ScriptResult(
            success=True,
            actions=tuple(actions),
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=completed.returncode,
            timed_out=False,
            error_message=None,
        )
        self._event_hook.on_script_finish(script_id, result)
        return result


def create_script_runner(event_hook: ScriptEventHook | None = None) -> ScriptRunner:
    """Convenience helper returning a :class:`ScriptRunner` instance."""

    return ScriptRunner(event_hook=event_hook)


def _decode_actions_payload(buffer: bytes) -> list[Action]:
    payload = buffer.strip()
    if not payload:
        return []
    raw = base64.b64decode(payload)
    data = pickle.loads(raw)
    if not isinstance(data, list):
        raise TypeError("Decoded payload is not a list of actions")
    for entry in data:
        if not isinstance(entry, _ACTION_TYPES):
            raise TypeError(f"Decoded payload contains non-action value: {entry!r}")
    return data


def _resolve_callable(module_name: str, qualname: str) -> Any:
    module = importlib.import_module(module_name)
    target: Any = module
    for segment in qualname.split("."):
        if segment == "<locals>":
            continue
        target = getattr(target, segment)
    return target


def _normalise_actions(value: Any) -> list[Action]:
    if value is None:
        return []
    if isinstance(value, _ACTION_TYPES):
        return [value]
    if isinstance(value, Iterable):
        actions: list[Action] = []
        for item in value:
            if not isinstance(item, _ACTION_TYPES):
                raise TypeError(f"Unsupported action type: {type(item)!r}")
            actions.append(item)
        return actions
    raise TypeError(f"Unexpected script result type: {type(value)!r}")


def _worker_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Contextipy script worker")
    parser.add_argument("--module", required=True, help="Module containing the target callable")
    parser.add_argument("--qualname", required=True, help="Qualname of the target callable")
    args = parser.parse_args(argv)

    try:
        payload = sys.stdin.read()
        input_data = ScriptInput.from_json(payload)
        target = _resolve_callable(args.module, args.qualname)

        call_kwargs = dict(input_data.parameters)
        if inspect.isfunction(target) or inspect.ismethod(target):
            signature = inspect.signature(target)
        else:
            signature = inspect.signature(getattr(target, "__call__"))

        if "selected_paths" in signature.parameters and "selected_paths" not in call_kwargs:
            call_kwargs["selected_paths"] = input_data.file_paths
        if "ask_answers" in signature.parameters and "ask_answers" not in call_kwargs:
            call_kwargs["ask_answers"] = input_data.ask_answers

        result = target(**call_kwargs)
        actions = _normalise_actions(result)
        encoded = base64.b64encode(pickle.dumps(actions)).decode("ascii")
        sys.stdout.write(encoded)
        sys.stdout.flush()
        return 0
    except Exception as exc:  # pragma: no cover - executed in subprocess
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(_worker_main())


__all__ = [
    "ScriptInput",
    "ScriptResult",
    "ScriptRunner",
    "ScriptEventHook",
    "DefaultEventHook",
    "create_script_runner",
]
