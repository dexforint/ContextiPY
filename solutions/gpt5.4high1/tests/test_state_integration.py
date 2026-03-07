from __future__ import annotations

from pathlib import Path

from pcontext.agent.registry import LiveRegistry
from pcontext.runtime.ipc_models import ShellContext, ShellEntry
from pcontext.runtime.shell import normalize_shell_context
from pcontext.storage.state import StateStore


def test_registry_uses_saved_oneshot_parameter_values_and_writes_log(
    tmp_path: Path,
) -> None:
    """
    Registry должен подставлять сохранённые значения параметров для oneshot-скрипта
    и записывать успешный запуск в лог.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)
    output_file = tmp_path / "oneshot_output.txt"

    script_path = scripts_root / "oneshot_with_param.py"
    script_path.write_text(
        f"""
from pathlib import Path
from typing import Annotated

from pcontext import Image, Param, oneshot_script

OUTPUT_PATH = Path(r"{output_file}")

@oneshot_script(
    id="script.saved_param",
    title="Saved param oneshot",
)
def run(
    image_path: Annotated[str, Image()],
    suffix: Annotated[str, Param(default="DEFAULT")],
) -> None:
    OUTPUT_PATH.write_text(image_path + "|" + suffix, encoding="utf-8")
    return None
""",
        encoding="utf-8",
    )

    state_store = StateStore(tmp_path / "state.db")
    state_store.set_parameter_value("script.saved_param", "suffix", "OVERRIDE")

    registry = LiveRegistry(scripts_root, state_store)

    try:
        context = ShellContext(
            source="selection",
            current_folder=str(tmp_path),
            entries=[
                ShellEntry(
                    path=str(tmp_path / "image.png"),
                    entry_type="file",
                )
            ],
        )

        result = registry.invoke(
            "script.saved_param",
            normalize_shell_context(context),
        )

        assert result.accepted is True
        assert output_file.exists() is True
        assert output_file.read_text(encoding="utf-8").endswith("|OVERRIDE")

        logs = state_store.list_run_logs(limit=10)
        assert len(logs) == 1
        assert logs[0].command_id == "script.saved_param"
        assert logs[0].success is True
    finally:
        registry.close()


def test_service_manager_uses_saved_service_init_parameters(tmp_path: Path) -> None:
    """
    Сервис должен стартовать с сохранёнными init-параметрами из SQLite.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)
    output_file = tmp_path / "service_output.txt"

    script_path = scripts_root / "service_with_param.py"
    script_path.write_text(
        f"""
from pathlib import Path
from typing import Annotated

from pcontext import Image, Param, Service

service = Service()


@service(
    id="service.saved_prefix",
    title="Saved prefix service",
)
class SavedPrefixService:
    def __init__(
        self,
        prefix: Annotated[str, Param(default="DEFAULT")],
    ) -> None:
        self.prefix = prefix
        self.output_path = Path(r"{output_file}")

    @service.script(
        id="service.saved_prefix.write",
        title="Write with prefix",
    )
    def write_with_prefix(
        self,
        image_path: Annotated[str, Image()],
    ) -> None:
        self.output_path.write_text(self.prefix + "|" + image_path, encoding="utf-8")
        return None
""",
        encoding="utf-8",
    )

    state_store = StateStore(tmp_path / "state.db")
    state_store.set_parameter_value("service.saved_prefix", "prefix", "OVERRIDE")

    registry = LiveRegistry(scripts_root, state_store)

    try:
        start_result = registry.start_service("service.saved_prefix")
        assert start_result.accepted is True

        context = ShellContext(
            source="selection",
            current_folder=str(tmp_path),
            entries=[
                ShellEntry(
                    path=str(tmp_path / "image.png"),
                    entry_type="file",
                )
            ],
        )

        invoke_result = registry.invoke(
            "service.saved_prefix.write",
            normalize_shell_context(context),
        )

        assert invoke_result.accepted is True
        assert output_file.exists() is True
        assert output_file.read_text(encoding="utf-8").startswith("OVERRIDE|")
    finally:
        registry.close()
