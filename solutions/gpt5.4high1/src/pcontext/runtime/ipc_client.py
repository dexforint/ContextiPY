from __future__ import annotations

import socket

from pcontext.runtime.ipc_models import (
    AgentEndpoint,
    REQUEST_ADAPTER,
    RESPONSE_ADAPTER,
    RequestMessage,
    ResponseMessage,
)


def send_request(
    endpoint: AgentEndpoint,
    request: RequestMessage,
    *,
    timeout_seconds: float = 3.0,
) -> ResponseMessage:
    """
    Отправляет один запрос агенту и получает один ответ.

    Протокол здесь очень простой:
    одна JSON-строка на вход, одна JSON-строка на выход.
    """
    payload = REQUEST_ADAPTER.dump_json(request) + b"\n"

    with socket.create_connection(
        (endpoint.host, endpoint.port), timeout=timeout_seconds
    ) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendall(payload)

        # После отправки данных мы явно говорим второй стороне,
        # что запрос закончен и можно формировать ответ.
        sock.shutdown(socket.SHUT_WR)

        with sock.makefile("rb") as reader:
            raw_response = reader.readline()

    if not raw_response:
        raise RuntimeError("Агент не прислал ответ.")

    return RESPONSE_ADAPTER.validate_json(raw_response)
