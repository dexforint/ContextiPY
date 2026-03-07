from __future__ import annotations

from pathlib import Path

from pcontext.agent.registry import LiveRegistry
from pcontext.storage.state import StateStore


def test_live_registry_can_invoke_direct_oneshot(tmp_path: Path) -> None:
    """
    GUI-запуск oneshot-скрипта без входных файлов должен реально работать.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)
    state_store = StateStore(tmp_path / "state.db")
    output_file = tmp_path / "direct_oneshot.txt"

    script_path = scripts_root / "direct_oneshot.py"
    script_path.write_text(
        f"""
from pathlib import Path
from typing import Annotated

from pcontext import Param, oneshot_script

OUTPUT_PATH = Path(r"{output_file}")

@oneshot_script(
    id="script.direct.oneshot",
    title="Direct oneshot",
)
def run(
    suffix: Annotated[str, Param(default="DEFAULT")],
) -> None:
    OUTPUT_PATH.write_text("OK|" + suffix, encoding="utf-8")
""",
        encoding="utf-8",
    )

    state_store.set_parameter_value("script.direct.oneshot", "suffix", "GUI")

    registry = LiveRegistry(scripts_root, state_store)

    try:
        result = registry.invoke_direct("script.direct.oneshot")

        assert result.accepted is True
        assert output_file.exists() is True
        assert output_file.read_text(encoding="utf-8") == "OK|GUI"

        logs = state_store.list_run_logs(limit=10)
        assert len(logs) == 1
        assert logs[0].context_json is None
    finally:
        registry.close()


def test_live_registry_can_invoke_direct_service_method(tmp_path: Path) -> None:
    """
    GUI-запуск service.script без входных файлов должен выполняться
    внутри уже запущенного сервиса.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)
    state_store = StateStore(tmp_path / "state.db")
    output_file = tmp_path / "direct_service.txt"

    script_path = scripts_root / "direct_service.py"
    script_path.write_text(
        f"""
from pathlib import Path
from typing import Annotated

from pcontext import Param, Service

service = Service()

@service(
    id="service.direct.demo",
    title="Direct service",
)
class DirectService:
    def __init__(
        self,
        prefix: Annotated[str, Param(default="DEFAULT")],
    ) -> None:
        self.prefix = prefix
        self.output_path = Path(r"{output_file}")

    @service.script(
        id="service.direct.demo.run",
        title="Direct run",
    )
    def run(
        self,
        suffix: Annotated[str, Param(default="X")],
    ) -> None:
        self.output_path.write_text(self.prefix + "|" + suffix, encoding="utf-8")
""",
        encoding="utf-8",
    )

    state_store.set_parameter_value("service.direct.demo", "prefix", "SERVICE")
    state_store.set_parameter_value("service.direct.demo.run", "suffix", "METHOD")

    registry = LiveRegistry(scripts_root, state_store)

    try:
        start_result = registry.start_service("service.direct.demo")
        assert start_result.accepted is True

        invoke_result = registry.invoke_direct("service.direct.demo.run")
        assert invoke_result.accepted is True

        assert output_file.exists() is True
        assert output_file.read_text(encoding="utf-8") == "SERVICE|METHOD"
    finally:
        registry.close()
