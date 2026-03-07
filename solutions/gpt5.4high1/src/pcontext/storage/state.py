from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pcontext.storage.models import RunLogRecord


class StateStore:
    """
    Простое SQLite-хранилище состояния PContext.

    Здесь хранятся:
    - настройки приложения;
    - сохранённые значения параметров;
    - логи запусков скриптов и сервисных методов.

    Для простоты каждая операция открывает своё короткое SQLite-соединение.
    Это хорошо работает с несколькими процессами и упрощает потокобезопасность.
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

        CREATE INDEX IF NOT EXISTS idx_run_logs_created_at
            ON run_logs(created_at_utc DESC);

        CREATE INDEX IF NOT EXISTS idx_run_logs_command_id
            ON run_logs(command_id);
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

        В качестве `owner_id` может выступать:
        - id oneshot-скрипта;
        - id сервиса;
        - id service.script-метода.
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

        Возвращает `True`, если запись действительно существовала.
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

        Возвращает число удалённых записей.
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

        Возвращает integer-id созданной записи.
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

    def _row_to_run_log(self, row: sqlite3.Row) -> RunLogRecord:
        """
        Преобразует SQLite-строку в типизированную запись лога.
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
