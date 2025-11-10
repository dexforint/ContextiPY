"""Demo script for the logs window."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("PySide6 is not installed. Please install it to run this demo.")
    sys.exit(1)

from contextipy.logging.logger import ExecutionLog
from contextipy.ui.windows.logs import LogsWindow


def create_mock_logs() -> list[ExecutionLog]:
    """Create mock execution logs for demonstration."""
    return [
        ExecutionLog(
            run_id="run-001-demo",
            script_id="demo-script-a",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            status="success",
            exit_code=0,
            timed_out=False,
            error_message=None,
            actions_summary=[{"type": "text", "content": "<redacted>"}],
            stdout_excerpt="Script executed successfully\nOutput line 2\nOutput line 3",
            stderr_excerpt="",
            input_payload={"parameters": {"key": "value"}},
        ),
        ExecutionLog(
            run_id="run-002-demo",
            script_id="demo-script-b",
            start_time=datetime(2024, 1, 1, 12, 1, 0),
            end_time=datetime(2024, 1, 1, 12, 1, 3),
            status="failure",
            exit_code=1,
            timed_out=False,
            error_message="Script failed with error",
            actions_summary=[],
            stdout_excerpt="",
            stderr_excerpt="Error: File not found\nTraceback...\nLine 42: file.txt not found",
            input_payload={"parameters": {}},
        ),
        ExecutionLog(
            run_id="run-003-demo",
            script_id="demo-script-a",
            start_time=datetime(2024, 1, 1, 12, 2, 0),
            end_time=datetime(2024, 1, 1, 12, 2, 15),
            status="error",
            exit_code=None,
            timed_out=True,
            error_message="Script exceeded timeout of 10s",
            actions_summary=[],
            stdout_excerpt="Processing...\nStill processing...\nTook too long...",
            stderr_excerpt="",
            input_payload={"parameters": {"timeout": 10}},
        ),
    ]


def get_logs_callback(limit: int, status: str | None, script_id: str | None) -> list[ExecutionLog]:
    """Mock callback to fetch logs."""
    logs = create_mock_logs()

    if status:
        logs = [log for log in logs if log.status == status]

    if script_id and script_id != "Все":
        logs = [log for log in logs if log.script_id == script_id]

    return logs[:limit]


def repeat_action_callback(run_id: str) -> tuple[bool, str | None]:
    """Mock callback for repeat action."""
    print(f"Repeat action called for run_id: {run_id}")
    return (True, None)


def main() -> None:
    """Run the logs window demo."""
    app = QApplication(sys.argv)

    window = LogsWindow(
        get_logs=get_logs_callback,
        repeat_action=repeat_action_callback,
    )

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
