from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pcontext.storage.models import (
    CommandUsageStats,
    RegistrationModuleRecord,
    RunLogRecord,
)


class StateStore:
    """
    Простое SQLite-хранилище состояния PContext.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path.expanduser().resolve()
        self._lock = threading.RLock()
        self.initialize()

    @property
    def database_path(self) -> Path:
        """
        Возвращает путь до файла базы данных.
        """
        return self._database_path

    def _connect(self) -> sqlite3.Connection:
        """
        Создаёт новое SQLite-соединение.
        """
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(
            self._database_path,
            timeout=30.0,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """
        Создаёт таблицы, если они ещё не существуют.
        """
        schema_sql = """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS parameter_values (
            owner_id TEXT NOT NULL,
            param_name TEXT NOT NULL,
            value_json TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (owner_id, param_name)
        );

        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at_utc TEXT NOT NULL,
            invocation_kind TEXT NOT NULL,
            command_id TEXT NOT NULL,
            title TEXT NOT NULL,
            duration_ms INTEGER NULL,
            success INTEGER NOT NULL,
            message TEXT NOT NULL,
            action_json TEXT NULL,
            context_json TEXT NULL
        );

        CREATE TABLE IF NOT EXISTS registration_modules (
            relative_path TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            file_hash_sha256 TEXT NOT NULL,
            dependencies_json TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT NULL,
            updated_at_utc TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_run_logs_created_at
            ON run_logs(created_at_utc DESC);

        CREATE INDEX IF NOT EXISTS idx_run_logs_command_id
            ON run_logs(command_id);

        CREATE INDEX IF NOT EXISTS idx_registration_modules_status
            ON registration_modules(status);
        """

        with self._lock, self._connect() as connection:
            connection.executescript(schema_sql)

    def _now_utc(self) -> str:
        """
        Возвращает текущее время в UTC в ISO-формате.
        """
        return datetime.now(timezone.utc).isoformat()

    def _dump_json(self, value: Any) -> str:
        """
        Сериализует значение в JSON.
        """
        return json.dumps(value, ensure_ascii=False)

    def _load_json(self, payload: str) -> Any:
        """
        Десериализует значение из JSON.
        """
        return json.loads(payload)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Возвращает сохранённую настройку приложения.
        """
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT value_json
                FROM app_settings
                WHERE key = ?
                """,
                (key,),
            ).fetchone()

        if row is None:
            return default

        return self._load_json(str(row["value_json"]))

    def set_setting(self, key: str, value: Any) -> None:
        """
        Сохраняет настройку приложения.
        """
        now_utc = self._now_utc()
        value_json = self._dump_json(value)

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO app_settings (key, value_json, updated_at_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (key, value_json, now_utc),
            )
            connection.commit()

    def get_parameter_values(self, owner_id: str) -> dict[str, Any]:
        """
        Возвращает все сохранённые параметры для одной сущности.
        """
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT param_name, value_json
                FROM parameter_values
                WHERE owner_id = ?
                ORDER BY param_name
                """,
                (owner_id,),
            ).fetchall()

        return {
            str(row["param_name"]): self._load_json(str(row["value_json"]))
            for row in rows
        }

    def set_parameter_value(self, owner_id: str, param_name: str, value: Any) -> None:
        """
        Сохраняет одно переопределённое значение параметра.
        """
        now_utc = self._now_utc()
        value_json = self._dump_json(value)

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO parameter_values (owner_id, param_name, value_json, updated_at_utc)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_id, param_name) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (owner_id, param_name, value_json, now_utc),
            )
            connection.commit()

    def reset_parameter_value(self, owner_id: str, param_name: str) -> bool:
        """
        Удаляет одно сохранённое переопределение параметра.
        """
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM parameter_values
                WHERE owner_id = ? AND param_name = ?
                """,
                (owner_id, param_name),
            )
            connection.commit()

        return cursor.rowcount > 0

    def reset_all_parameter_values(self, owner_id: str) -> int:
        """
        Удаляет все сохранённые переопределения параметров сущности.
        """
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM parameter_values
                WHERE owner_id = ?
                """,
                (owner_id,),
            )
            connection.commit()

        return int(cursor.rowcount)

    def add_run_log(
        self,
        *,
        invocation_kind: str,
        command_id: str,
        title: str,
        duration_ms: int | None,
        success: bool,
        message: str,
        action_json: str | None,
        context_json: str | None,
    ) -> int:
        """
        Добавляет новую запись в лог запусков.
        """
        created_at_utc = self._now_utc()

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO run_logs (
                    created_at_utc,
                    invocation_kind,
                    command_id,
                    title,
                    duration_ms,
                    success,
                    message,
                    action_json,
                    context_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at_utc,
                    invocation_kind,
                    command_id,
                    title,
                    duration_ms,
                    1 if success else 0,
                    message,
                    action_json,
                    context_json,
                ),
            )
            connection.commit()

        return int(cursor.lastrowid)

    def list_run_logs(self, limit: int = 50) -> list[RunLogRecord]:
        """
        Возвращает последние записи лога, начиная с самых новых.
        """
        safe_limit = max(1, int(limit))

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at_utc,
                    invocation_kind,
                    command_id,
                    title,
                    duration_ms,
                    success,
                    message,
                    action_json,
                    context_json
                FROM run_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        return [self._row_to_run_log(row) for row in rows]

    def get_run_log(self, log_id: int) -> RunLogRecord | None:
        """
        Возвращает одну запись лога по id.
        """
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    created_at_utc,
                    invocation_kind,
                    command_id,
                    title,
                    duration_ms,
                    success,
                    message,
                    action_json,
                    context_json
                FROM run_logs
                WHERE id = ?
                """,
                (int(log_id),),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_run_log(row)

    def upsert_registration_module(
        self,
        *,
        relative_path: str,
        source_file: str,
        file_hash_sha256: str,
        dependencies: list[str],
        status: str,
        error_message: str | None,
    ) -> None:
        """
        Сохраняет снимок регистрации одного файла из scripts.
        """
        updated_at_utc = self._now_utc()
        dependencies_json = self._dump_json(dependencies)

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO registration_modules (
                    relative_path,
                    source_file,
                    file_hash_sha256,
                    dependencies_json,
                    status,
                    error_message,
                    updated_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(relative_path) DO UPDATE SET
                    source_file = excluded.source_file,
                    file_hash_sha256 = excluded.file_hash_sha256,
                    dependencies_json = excluded.dependencies_json,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (
                    relative_path,
                    source_file,
                    file_hash_sha256,
                    dependencies_json,
                    status,
                    error_message,
                    updated_at_utc,
                ),
            )
            connection.commit()

    def list_registration_modules(self) -> list[RegistrationModuleRecord]:
        """
        Возвращает все сохранённые снимки регистрации.
        """
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    relative_path,
                    source_file,
                    file_hash_sha256,
                    dependencies_json,
                    status,
                    error_message,
                    updated_at_utc
                FROM registration_modules
                ORDER BY relative_path
                """
            ).fetchall()

        return [self._row_to_registration_module(row) for row in rows]

    def delete_registration_module(self, relative_path: str) -> bool:
        """
        Удаляет снимок регистрации для файла, которого больше нет.
        """
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM registration_modules
                WHERE relative_path = ?
                """,
                (relative_path,),
            )
            connection.commit()

        return cursor.rowcount > 0

    def list_command_usage_stats(
        self, command_ids: list[str]
    ) -> dict[str, CommandUsageStats]:
        """
        Возвращает статистику использования команд.

        В статистику включаются только реальные запуски oneshot/service_script,
        но не служебные launcher-события.
        """
        normalized_command_ids = [item for item in command_ids if item]
        if not normalized_command_ids:
            return {}

        placeholders = ", ".join("?" for _ in normalized_command_ids)

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    command_id,
                    COUNT(*) AS launch_count,
                    MAX(created_at_utc) AS last_used_utc
                FROM run_logs
                WHERE command_id IN ({placeholders})
                  AND invocation_kind IN ('oneshot_script', 'service_script')
                GROUP BY command_id
                """,
                tuple(normalized_command_ids),
            ).fetchall()

        return {
            str(row["command_id"]): CommandUsageStats(
                command_id=str(row["command_id"]),
                launch_count=int(row["launch_count"]),
                last_used_utc=(
                    str(row["last_used_utc"])
                    if row["last_used_utc"] is not None
                    else None
                ),
            )
            for row in rows
        }

    def _row_to_run_log(self, row: sqlite3.Row) -> RunLogRecord:
        """
        Преобразует SQLite-строку в запись лога.
        """
        return RunLogRecord(
            log_id=int(row["id"]),
            created_at_utc=str(row["created_at_utc"]),
            invocation_kind=str(row["invocation_kind"]),  # type: ignore[arg-type]
            command_id=str(row["command_id"]),
            title=str(row["title"]),
            duration_ms=(
                int(row["duration_ms"]) if row["duration_ms"] is not None else None
            ),
            success=bool(int(row["success"])),
            message=str(row["message"]),
            action_json=(
                str(row["action_json"]) if row["action_json"] is not None else None
            ),
            context_json=(
                str(row["context_json"]) if row["context_json"] is not None else None
            ),
        )

    def _row_to_registration_module(self, row: sqlite3.Row) -> RegistrationModuleRecord:
        """
        Преобразует SQLite-строку в снимок регистрации файла.
        """
        return RegistrationModuleRecord(
            relative_path=str(row["relative_path"]),
            source_file=str(row["source_file"]),
            file_hash_sha256=str(row["file_hash_sha256"]),
            dependencies=self._load_json(str(row["dependencies_json"])),
            status=str(row["status"]),  # type: ignore[arg-type]
            error_message=(
                str(row["error_message"]) if row["error_message"] is not None else None
            ),
            updated_at_utc=str(row["updated_at_utc"]),
        )
