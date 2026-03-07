from __future__ import annotations

from pathlib import Path

from pcontext.runner.models import ExecutionErrorResponse, OneshotExecutionRequest
from pcontext.runner.subprocess_runner import execute_oneshot_in_subprocess
from pcontext.runtime.ipc_models import ShellContext, ShellEntry


def test_execute_oneshot_in_subprocess_returns_copy_action(tmp_path: Path) -> None:
    """
    Oneshot-скрипт должен реально выполниться в отдельном процессе
    и вернуть сериализованное действие Copy.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "sample.py"
    script_path.write_text(
        """
from typing import Annotated
from pcontext import Image, Param, oneshot_script
from pcontext.actions import Copy

@oneshot_script(
    id="script.copy_result",
    title="Copy result",
)
def run(
    image_path: Annotated[str, Image()],
    quality: Annotated[int, Param(default=95, ge=1, le=100)],
) -> Copy:
    return Copy(f"{image_path}|{quality}")
""",
        encoding="utf-8",
    )

    request = OneshotExecutionRequest(
        scripts_root=str(scripts_root),
        source_file=str(script_path),
        qualname="run",
        context=ShellContext(
            source="selection",
            current_folder=str(tmp_path),
            entries=[
                ShellEntry(
                    path=str(tmp_path / "image.png"),
                    entry_type="file",
                )
            ],
        ),
        parameter_values={},
    )

    response = execute_oneshot_in_subprocess(request)

    assert not isinstance(response, ExecutionErrorResponse)
    assert response.action.kind == "copy"
    assert response.action.text.endswith("|95")


def test_execute_oneshot_in_subprocess_returns_error_response(tmp_path: Path) -> None:
    """
    Ошибка внутри пользовательского скрипта должна вернуться структурированно,
    а не ронять основной процесс.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "broken.py"
    script_path.write_text(
        """
from typing import Annotated
from pcontext import Image, oneshot_script

@oneshot_script(
    id="script.broken",
    title="Broken script",
)
def run(
    image_path: Annotated[str, Image()],
) -> None:
    raise RuntimeError("Boom")
""",
        encoding="utf-8",
    )

    request = OneshotExecutionRequest(
        scripts_root=str(scripts_root),
        source_file=str(script_path),
        qualname="run",
        context=ShellContext(
            source="selection",
            current_folder=str(tmp_path),
            entries=[
                ShellEntry(
                    path=str(tmp_path / "image.png"),
                    entry_type="file",
                )
            ],
        ),
        parameter_values={},
    )

    response = execute_oneshot_in_subprocess(request)

    assert isinstance(response, ExecutionErrorResponse)
    assert response.error_type == "RuntimeError"
    assert "Boom" in response.message
