from __future__ import annotations

import subprocess
import sys

from pcontext.runner.models import (
    EXECUTION_RESPONSE_ADAPTER,
    ExecutionErrorResponse,
    ExecutionResponse,
    OneshotExecutionRequest,
)


def execute_oneshot_in_subprocess(
    request: OneshotExecutionRequest,
) -> ExecutionResponse:
    """
    Выполняет oneshot-скрипт в отдельном Python-процессе.
    """
    command = [
        sys.executable,
        "-m",
        "pcontext.runner.worker",
    ]

    completed = subprocess.run(
        command,
        input=request.model_dump_json(indent=2),
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr_text = (
            completed.stderr.strip() or "Worker завершился с неизвестной ошибкой."
        )
        raise RuntimeError(
            f"Процесс выполнения скрипта завершился с кодом {completed.returncode}: {stderr_text}"
        )

    stdout_text = completed.stdout.strip()
    if not stdout_text:
        raise RuntimeError("Worker не вернул JSON-ответ.")

    response = EXECUTION_RESPONSE_ADAPTER.validate_json(stdout_text)

    if isinstance(response, ExecutionErrorResponse):
        return response

    return response
