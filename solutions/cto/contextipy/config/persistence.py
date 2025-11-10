"""Persistence helpers for scripts, parameters, settings, and logs."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar, cast

from .paths import (
    ensure_directory,
    get_logs_dir,
    get_menu_visibility_path,
    get_parameters_path,
    get_registry_path,
)

T = TypeVar("T")


class VersionedJsonStore(Generic[T]):
    """Store that persists JSON payloads alongside a schema version."""

    def __init__(
        self,
        path: Path,
        version: int,
        default_factory: Callable[[], T],
    ) -> None:
        self._path = path
        self._version = version
        self._default_factory = default_factory

    @property
    def path(self) -> Path:
        return self._path

    @property
    def version(self) -> int:
        return self._version

    def load(self) -> T:
        if not self._path.exists():
            return self._default_factory()

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return self._default_factory()

        if isinstance(raw, dict) and "version" in raw:
            file_version = raw.get("version")
            if file_version is None:
                return cast(T, dict(raw))

            try:
                file_version_int = int(file_version)
            except (TypeError, ValueError):
                return self._default_factory()

            if file_version_int > self._version:
                message = (
                    f"Stored data version {file_version_int} is newer than supported "
                    f"version {self._version}"
                )
                raise RuntimeError(message)

            payload = raw.get("payload", self._default_factory())
            if isinstance(payload, dict):
                return cast(T, dict(payload))
            return cast(T, payload)

        if isinstance(raw, dict):
            return cast(T, dict(raw))

        return self._default_factory()

    def save(self, payload: T) -> None:
        data = {"version": self._version, "payload": payload}
        ensure_directory(self._path.parent)
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)


class ScriptParameterStore(VersionedJsonStore[dict[str, Any]]):
    """Persists script parameter values with schema versioning."""

    VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(path or get_parameters_path(), self.VERSION, dict)

    def load_parameters(self) -> dict[str, Any]:
        return self.load()

    def save_parameters(self, parameters: Mapping[str, Any]) -> None:
        super().save(dict(parameters))


class MenuVisibilityStore(VersionedJsonStore[dict[str, bool]]):
    """Persists menu item visibility flags with versioning."""

    VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(path or get_menu_visibility_path(), self.VERSION, dict)

    def load_flags(self) -> dict[str, bool]:
        data = self.load()
        return {k: bool(v) for k, v in data.items()}

    def save_flags(self, flags: Mapping[str, bool]) -> None:
        normalized = {k: bool(v) for k, v in flags.items()}
        super().save(normalized)


class LogStore:
    """Simple append/read log storage within the app logs directory."""

    def __init__(self, filename: str = "contextipy.log", directory: Path | None = None) -> None:
        base_dir = ensure_directory(directory) if directory else get_logs_dir()
        self._path = base_dir / filename
        ensure_directory(self._path.parent)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, message: str) -> None:
        ensure_directory(self._path.parent)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(message)
            if not message.endswith("\n"):
                fh.write("\n")

    def read(self) -> list[str]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as fh:
            return [line.rstrip("\n") for line in fh]


class ScriptRegistry:
    """SQLite-backed storage for registered scripts."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_registry_path()
        ensure_directory(self._path.parent)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS scripts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )
            conn.commit()

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
        if row is None:
            return self.SCHEMA_VERSION
        return int(row[0])

    def save_script(self, script_id: str, payload: Mapping[str, Any]) -> None:
        serialized = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO scripts (id, payload) VALUES (?, ?)\n"
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (script_id, serialized),
            )
            conn.commit()

    def load_script(self, script_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM scripts WHERE id = ?",
                (script_id,),
            ).fetchone()
        if row is None:
            msg = f"Script '{script_id}' is not registered"
            raise KeyError(msg)
        return cast(dict[str, Any], json.loads(row[0]))

    def remove_script(self, script_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
            conn.commit()

    def list_scripts(self) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, payload FROM scripts ORDER BY id").fetchall()
        return {row[0]: cast(dict[str, Any], json.loads(row[1])) for row in rows}


@dataclass(frozen=True, slots=True)
class ExecutionLogRecord:
    """Persisted representation of a single script execution run."""

    run_id: str
    script_id: str
    status: str
    started_at: datetime
    finished_at: datetime
    duration: float
    actions_summary_json: str
    stdout_excerpt: str
    stderr_excerpt: str
    exit_code: int | None
    timed_out: bool
    error_message: str | None
    input_payload: str
    actions_payload: bytes


class ExecutionLogStore:
    """SQLite-backed storage for script execution logs."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        default_path = get_logs_dir() / "execution_logs.db"
        self._path = path or default_path
        ensure_directory(self._path.parent)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    script_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration REAL NOT NULL,
                    actions_summary_json TEXT NOT NULL,
                    stdout_excerpt TEXT NOT NULL,
                    stderr_excerpt TEXT NOT NULL,
                    exit_code INTEGER,
                    timed_out INTEGER NOT NULL,
                    error_message TEXT,
                    input_payload TEXT NOT NULL,
                    actions_payload BLOB NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_script_id ON runs(script_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
            conn.commit()

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'",
            ).fetchone()
        if row is None:
            return self.SCHEMA_VERSION
        return int(row[0])

    def record(self, record: ExecutionLogRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id,
                    script_id,
                    status,
                    started_at,
                    finished_at,
                    duration,
                    actions_summary_json,
                    stdout_excerpt,
                    stderr_excerpt,
                    exit_code,
                    timed_out,
                    error_message,
                    input_payload,
                    actions_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    script_id=excluded.script_id,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    duration=excluded.duration,
                    actions_summary_json=excluded.actions_summary_json,
                    stdout_excerpt=excluded.stdout_excerpt,
                    stderr_excerpt=excluded.stderr_excerpt,
                    exit_code=excluded.exit_code,
                    timed_out=excluded.timed_out,
                    error_message=excluded.error_message,
                    input_payload=excluded.input_payload,
                    actions_payload=excluded.actions_payload
                """,
                (
                    record.run_id,
                    record.script_id,
                    record.status,
                    record.started_at.isoformat(),
                    record.finished_at.isoformat(),
                    float(record.duration),
                    record.actions_summary_json,
                    record.stdout_excerpt,
                    record.stderr_excerpt,
                    record.exit_code,
                    1 if record.timed_out else 0,
                    record.error_message,
                    record.input_payload,
                    record.actions_payload,
                ),
            )
            conn.commit()

    def fetch_recent(
        self,
        *,
        limit: int = 20,
        script_id: str | None = None,
        status: str | None = None,
    ) -> list[ExecutionLogRecord]:
        query = "SELECT * FROM runs"
        clauses: list[str] = []
        params: list[Any] = []

        if script_id is not None:
            clauses.append("script_id = ?")
            params.append(script_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_record(row) for row in rows]

    def get_run(self, run_id: str) -> ExecutionLogRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

        if row is None:
            return None
        return self._row_to_record(row)

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runs")
            conn.commit()

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _row_to_record(self, row: tuple[Any, ...]) -> ExecutionLogRecord:
        started_at = self._parse_datetime(row[3])
        finished_at = self._parse_datetime(row[4])
        stdout_excerpt = row[7] if row[7] is not None else ""
        stderr_excerpt = row[8] if row[8] is not None else ""
        error_message = row[11] if row[11] is not None else None
        payload = row[13]
        if isinstance(payload, memoryview):
            actions_payload = payload.tobytes()
        else:
            actions_payload = bytes(payload)

        return ExecutionLogRecord(
            run_id=row[0],
            script_id=row[1],
            status=row[2],
            started_at=started_at,
            finished_at=finished_at,
            duration=float(row[5]),
            actions_summary_json=row[6],
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
            exit_code=row[9],
            timed_out=bool(row[10]),
            error_message=error_message,
            input_payload=row[12],
            actions_payload=actions_payload,
        )


__all__ = [
    "VersionedJsonStore",
    "ScriptParameterStore",
    "MenuVisibilityStore",
    "LogStore",
    "ScriptRegistry",
    "ExecutionLogRecord",
    "ExecutionLogStore",
]
