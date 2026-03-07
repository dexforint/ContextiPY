from __future__ import annotations

import inspect
import time
from pathlib import Path

from pcontext.registrar.introspection import import_module_from_path
from pcontext.runner.bindings import build_callable_kwargs, resolve_object_by_qualname
from pcontext.runner.models import ExecutionSuccessResponse, OneshotExecutionRequest
from pcontext.runtime.action_codec import serialize_action_result


def execute_oneshot_request(
    request: OneshotExecutionRequest,
) -> ExecutionSuccessResponse:
    """
    Выполняет oneshot-скрипт и возвращает сериализованный результат.
    """
    source_file = Path(request.source_file).expanduser().resolve()
    scripts_root = Path(request.scripts_root).expanduser().resolve()

    module = import_module_from_path(
        source_file,
        scripts_root=scripts_root,
    )
    target_object = resolve_object_by_qualname(module, request.qualname)

    if not callable(target_object):
        raise TypeError("Целевой объект oneshot-скрипта не является вызываемым.")

    if inspect.iscoroutinefunction(target_object):
        raise TypeError("Асинхронные скрипты пока не поддерживаются.")

    kwargs = build_callable_kwargs(
        target_object,
        context=request.context,
        parameter_values=request.parameter_values,
        skip_self=False,
    )

    started_at = time.perf_counter()
    result = target_object(**kwargs)
    duration_ms = int((time.perf_counter() - started_at) * 1000)

    serialized_action = serialize_action_result(result)

    return ExecutionSuccessResponse(
        action=serialized_action,
        duration_ms=duration_ms,
    )
