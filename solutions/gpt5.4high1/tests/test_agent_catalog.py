from __future__ import annotations

from pathlib import Path

from pcontext.agent.catalog import load_agent_catalog
from pcontext.agent.registry import LiveRegistry
from pcontext.runtime.ipc_models import ShellContext, ShellEntry
from pcontext.runtime.shell import normalize_shell_context


def test_agent_catalog_builds_real_context_commands(tmp_path: Path) -> None:
    """
    Каталог агента должен строить shell-команды по реальным пользовательским манифестам.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "sample.py"
    script_path.write_text(
        """
from typing import Annotated

from pcontext import Image, Param, Service, oneshot_script

service = Service()


@oneshot_script(
    id="script.visible_image",
    title="Visible image script",
)
def visible_image(
    image_path: Annotated[str, Image()],
) -> None:
    return None


@oneshot_script(
    id="script.direct_only",
    title="Direct only script",
)
def direct_only() -> None:
    return None


@service(
    id="service.detector",
    title="Detector service",
)
class Detector:
    def __init__(
        self,
        threshold: Annotated[float, Param(default=0.5, ge=0.0, le=1.0)],
    ) -> None:
        self.threshold = threshold

    @service.script(
        id="service.detector.detect",
        title="Detect on image",
    )
    def detect(
        self,
        image_path: Annotated[str, Image()],
    ) -> None:
        return None
""",
        encoding="utf-8",
    )

    catalog = load_agent_catalog(scripts_root)

    command_titles = [item.title for item in catalog.context_commands]
    assert "Visible image script" in command_titles
    assert "Detect on image" in command_titles
    assert "Direct only script" not in command_titles
    assert len(catalog.services) == 1
    assert len(catalog.failures) == 0


def test_live_registry_hides_service_methods_until_service_is_running(
    tmp_path: Path,
) -> None:
    """
    Метод сервиса должен появляться в shell-меню только после реального запуска сервиса.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "service_sample.py"
    script_path.write_text(
        """
from typing import Annotated

from pcontext import Image, Service

service = Service()


@service(
    id="service.detector",
    title="Detector service",
)
class Detector:
    def __init__(self) -> None:
        pass

    @service.script(
        id="service.detector.detect",
        title="Detect on image",
    )
    def detect(
        self,
        image_path: Annotated[str, Image()],
    ) -> None:
        return None
""",
        encoding="utf-8",
    )

    registry = LiveRegistry(scripts_root)

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
        normalized_context = normalize_shell_context(context)

        titles_before = [
            item.title for item in registry.list_menu_items(normalized_context)
        ]
        assert "Detect on image" not in titles_before

        start_result = registry.start_service("service.detector")
        assert start_result.accepted is True

        titles_after = [
            item.title for item in registry.list_menu_items(normalized_context)
        ]
        assert "Detect on image" in titles_after
    finally:
        registry.close()


def test_live_registry_reload_picks_up_new_script(tmp_path: Path) -> None:
    """
    После reload агент должен увидеть новый пользовательский скрипт.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    registry = LiveRegistry(scripts_root)

    try:
        assert len(registry.catalog.context_commands) == 0

        script_path = scripts_root / "new_script.py"
        script_path.write_text(
            """
from typing import Annotated
from pcontext import Image, oneshot_script

@oneshot_script(
    id="script.new_image",
    title="New image script",
)
def run(
    image_path: Annotated[str, Image()],
) -> None:
    return None
""",
            encoding="utf-8",
        )

        result = registry.reload()

        assert result.command_count == 1
        assert result.service_count == 0
        assert result.failure_count == 0
        assert registry.catalog.context_commands[0].title == "New image script"
    finally:
        registry.close()


def test_live_registry_invokes_real_oneshot_script(tmp_path: Path) -> None:
    """
    Реальный oneshot-скрипт должен запускаться через registry.invoke.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "invoke_sample.py"
    script_path.write_text(
        """
from typing import Annotated
from pcontext import Image, oneshot_script

@oneshot_script(
    id="script.invoke_real",
    title="Invoke real",
)
def run(
    image_path: Annotated[str, Image()],
) -> None:
    return None
""",
        encoding="utf-8",
    )

    registry = LiveRegistry(scripts_root)

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
            "script.invoke_real",
            normalize_shell_context(context),
        )

        assert result.accepted is True
        assert "успешно выполнен" in result.message
    finally:
        registry.close()


def test_live_registry_invokes_real_service_method(tmp_path: Path) -> None:
    """
    Реальный service.script должен выполняться внутри уже запущенного сервиса.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    marker_file = tmp_path / "service_marker.txt"

    script_path = scripts_root / "service_invoke_sample.py"
    script_path.write_text(
        f"""
from pathlib import Path
from typing import Annotated

from pcontext import Image, Service

service = Service()


@service(
    id="service.marker",
    title="Marker service",
)
class MarkerService:
    def __init__(self) -> None:
        self.output_path = Path(r"{marker_file}")

    @service.script(
        id="service.marker.write",
        title="Write marker",
    )
    def write_marker(
        self,
        image_path: Annotated[str, Image()],
    ) -> None:
        self.output_path.write_text(image_path, encoding="utf-8")
        return None
""",
        encoding="utf-8",
    )

    registry = LiveRegistry(scripts_root)

    try:
        start_result = registry.start_service("service.marker")
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

        result = registry.invoke(
            "service.marker.write",
            normalize_shell_context(context),
        )

        assert result.accepted is True
        assert marker_file.exists() is True
        assert marker_file.read_text(encoding="utf-8").endswith("image.png")
    finally:
        registry.close()
