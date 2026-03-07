from __future__ import annotations

import sys
import traceback

from pcontext.runner.execution import execute_oneshot_request
from pcontext.runner.models import (
    EXECUTION_REQUEST_ADAPTER,
    ExecutionErrorResponse,
)


def main() -> int:
    """
    Точка входа worker-процесса выполнения.

    Процесс получает JSON-запрос через stdin и всегда пытается
    вернуть структурированный JSON-ответ через stdout.
    """
    raw_request = sys.stdin.read()

    try:
        if not raw_request.strip():
            raise ValueError("Worker не получил входной JSON-запрос.")

        request = EXECUTION_REQUEST_ADAPTER.validate_json(raw_request)
        response = execute_oneshot_request(request)
    except Exception as error:  # noqa: BLE001
        response = ExecutionErrorResponse(
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
        )

    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
