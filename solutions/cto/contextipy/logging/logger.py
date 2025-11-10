"""Script execution logging with metadata persistence and query APIs.

This module provides structured logging for script executions, capturing metadata
such as run IDs, timestamps, status, actions, and I/O excerpts. It integrates with
the script runner event hooks and persists data via SQLite using the
ExecutionLogStore from the persistence layer.
"""

from __future__ import annotations

import json
import pickle
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from contextipy.actions import Action, serialize_actions_for_log
from contextipy.config.persistence import ExecutionLogRecord, ExecutionLogStore
from contextipy.execution.script_runner import ScriptEventHook, ScriptInput, ScriptResult

MAX_STDOUT_LENGTH = 2048
MAX_STDERR_LENGTH = 2048


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


@dataclass(frozen=True, slots=True)
class ExecutionLog:
    """Record of a single script execution with metadata."""

    run_id: str
    script_id: str
    start_time: datetime
    end_time: datetime
    status: str
    exit_code: int | None = None
    timed_out: bool = False
    error_message: str | None = None
    actions_summary: list[dict[str, Any]] = field(default_factory=list)
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    input_payload: dict[str, Any] = field(default_factory=dict)
    actions: tuple[Action, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Convert the log record to a dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "script_id": self.script_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "error_message": self.error_message,
            "actions_summary": self.actions_summary,
            "stdout_excerpt": self.stdout_excerpt,
            "stderr_excerpt": self.stderr_excerpt,
            "input_payload": self.input_payload,
        }


class ExecutionLogger(ScriptEventHook):
    """Logger for script executions that persists to SQLite and provides query APIs.

    This logger implements the ScriptEventHook protocol and can be passed to the
    ScriptRunner to automatically log all script executions. It captures metadata
    including run IDs, timestamps, status, actions, and I/O excerpts, persisting
    them via the ExecutionLogStore. It provides query APIs for retrieving recent
    runs, filtering by status or script, and rehydrating input payloads for
    repeat execution.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the execution logger.

        Args:
            path: Optional path to the SQLite database. If None, uses default log directory.
        """
        self._store = ExecutionLogStore(path=path)
        self._active_runs: dict[str, tuple[str, datetime, ScriptInput]] = {}

    @property
    def path(self) -> Path:
        """Return the path to the database."""
        return self._store.path

    def on_script_start(self, script_id: str, input_data: ScriptInput) -> None:
        """Invoked when a script execution begins.

        Generates a unique run ID and stores the start time and input data.
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()
        self._active_runs[script_id] = (run_id, start_time, input_data)

    def on_script_finish(self, script_id: str, result: ScriptResult) -> None:
        """Invoked when a script execution completes.

        Records the execution log with all metadata including status, actions,
        and output excerpts.
        """
        if script_id not in self._active_runs:
            return

        run_id, start_time, input_data = self._active_runs.pop(script_id)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        status = "success" if result.success else "failure"
        actions_summary = serialize_actions_for_log(result.actions, redacted=False)
        stdout_excerpt = _truncate_text(result.stdout, MAX_STDOUT_LENGTH)
        stderr_excerpt = _truncate_text(result.stderr, MAX_STDERR_LENGTH)

        input_payload = {
            "file_paths": [str(p) for p in input_data.file_paths],
            "parameters": input_data.parameters,
            "ask_answers": input_data.ask_answers,
        }

        actions_payload = pickle.dumps(result.actions)

        record = ExecutionLogRecord(
            run_id=run_id,
            script_id=script_id,
            status=status,
            started_at=start_time,
            finished_at=end_time,
            duration=duration,
            actions_summary_json=json.dumps(actions_summary, ensure_ascii=False),
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            error_message=result.error_message,
            input_payload=json.dumps(input_payload, ensure_ascii=False),
            actions_payload=actions_payload,
        )

        self._store.record(record)

    def on_script_error(self, script_id: str, error: Exception) -> None:
        """Invoked when an unexpected error occurs during execution.

        Records the error in the execution log.
        """
        if script_id not in self._active_runs:
            return

        run_id, start_time, input_data = self._active_runs.pop(script_id)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        input_payload = {
            "file_paths": [str(p) for p in input_data.file_paths],
            "parameters": input_data.parameters,
            "ask_answers": input_data.ask_answers,
        }

        record = ExecutionLogRecord(
            run_id=run_id,
            script_id=script_id,
            status="error",
            started_at=start_time,
            finished_at=end_time,
            duration=duration,
            actions_summary_json="[]",
            stdout_excerpt="",
            stderr_excerpt="",
            exit_code=None,
            timed_out=False,
            error_message=str(error),
            input_payload=json.dumps(input_payload, ensure_ascii=False),
            actions_payload=pickle.dumps(()),
        )

        self._store.record(record)

    def get_recent_runs(self, limit: int = 50) -> list[ExecutionLog]:
        """Get the most recent execution logs.

        Args:
            limit: Maximum number of logs to return (default: 50).

        Returns:
            List of ExecutionLog instances ordered by start time descending.
        """
        records = self._store.fetch_recent(limit=limit)
        return [self._record_to_log(record) for record in records]

    def get_runs_by_status(self, status: str, limit: int = 50) -> list[ExecutionLog]:
        """Get execution logs filtered by status.

        Args:
            status: The status to filter by (e.g., 'success', 'failure', 'error').
            limit: Maximum number of logs to return (default: 50).

        Returns:
            List of ExecutionLog instances ordered by start time descending.
        """
        records = self._store.fetch_recent(limit=limit, status=status)
        return [self._record_to_log(record) for record in records]

    def get_runs_by_script(self, script_id: str, limit: int = 50) -> list[ExecutionLog]:
        """Get execution logs for a specific script.

        Args:
            script_id: The script ID to filter by.
            limit: Maximum number of logs to return (default: 50).

        Returns:
            List of ExecutionLog instances ordered by start time descending.
        """
        records = self._store.fetch_recent(limit=limit, script_id=script_id)
        return [self._record_to_log(record) for record in records]

    def get_run_by_id(self, run_id: str) -> ExecutionLog | None:
        """Get a specific execution log by run ID.

        Args:
            run_id: The run ID to retrieve.

        Returns:
            ExecutionLog instance or None if not found.
        """
        record = self._store.get_run(run_id)
        if record is None:
            return None
        return self._record_to_log(record)

    def get_active_runs(self) -> dict[str, tuple[str, datetime, ScriptInput]]:
        """Get currently active (running) script executions.

        Returns:
            Dictionary mapping script_id to (run_id, start_time, input_data) tuples.
        """
        return dict(self._active_runs)

    def rehydrate_input(self, run_id: str) -> ScriptInput:
        """Rehydrate the input payload from a previous run for repeat execution.

        This allows re-running a script with the exact same inputs as a previous
        execution by providing the run ID.

        Args:
            run_id: The run ID to rehydrate input from.

        Returns:
            ScriptInput instance with the original input data.

        Raises:
            KeyError: If the run ID is not found.
        """
        record = self._store.get_run(run_id)
        if record is None:
            msg = f"Run '{run_id}' not found"
            raise KeyError(msg)

        input_payload = json.loads(record.input_payload)
        file_paths = tuple(Path(p) for p in input_payload.get("file_paths", []))
        parameters = input_payload.get("parameters", {})
        ask_answers = input_payload.get("ask_answers", {})

        return ScriptInput(
            file_paths=file_paths,
            parameters=parameters,
            ask_answers=ask_answers,
        )

    def _record_to_log(self, record: ExecutionLogRecord) -> ExecutionLog:
        """Convert an ExecutionLogRecord to an ExecutionLog instance."""
        actions_summary = json.loads(record.actions_summary_json)
        input_payload = json.loads(record.input_payload)
        actions = pickle.loads(record.actions_payload)

        return ExecutionLog(
            run_id=record.run_id,
            script_id=record.script_id,
            start_time=record.started_at,
            end_time=record.finished_at,
            status=record.status,
            exit_code=record.exit_code,
            timed_out=record.timed_out,
            error_message=record.error_message,
            actions_summary=actions_summary,
            stdout_excerpt=record.stdout_excerpt,
            stderr_excerpt=record.stderr_excerpt,
            input_payload=input_payload,
            actions=tuple(actions),
        )


__all__ = [
    "ExecutionLogger",
    "ExecutionLog",
    "MAX_STDOUT_LENGTH",
    "MAX_STDERR_LENGTH",
]
