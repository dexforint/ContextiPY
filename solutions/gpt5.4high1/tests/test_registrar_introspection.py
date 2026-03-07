from __future__ import annotations

from pathlib import Path

from pcontext.registrar.introspection import inspect_script_file


def test_inspect_oneshot_script(tmp_path: Path) -> None:
    """
    Регистратор должен извлекать oneshot-скрипт, его входы и параметры.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "sample.py"
    script_path.write_text(
        '''
"""
requests>=2.31
"""
from typing import Annotated
from enum import Enum

from pcontext import Image, Param, oneshot_script


class Mode(str, Enum):
    fast = "fast"
    slow = "slow"


@oneshot_script(
    title="Resize image",
    description="Resize selected image",
    timeout=10,
)
def resize_image(
    image_path: Annotated[str, Image()],
    mode: Annotated[Mode, Param(default="fast")],
) -> None:
    return None
''',
        encoding="utf-8",
    )

    result = inspect_script_file(script_path, scripts_root=scripts_root)

    assert result.dependencies == ["requests>=2.31"]
    assert len(result.oneshot_scripts) == 1
    assert len(result.services) == 0

    script_manifest = result.oneshot_scripts[0]
    assert script_manifest.title == "Resize image"
    assert script_manifest.supports_direct_run is False
    assert len(script_manifest.inputs) == 1
    assert len(script_manifest.params) == 1
    assert script_manifest.inputs[0].name == "image_path"
    assert script_manifest.params[0].name == "mode"
    assert script_manifest.params[0].value_type.kind == "enum"


def test_inspect_service_with_method(tmp_path: Path) -> None:
    """
    Регистратор должен извлекать сервис, его init-параметры и script-методы.
    """
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir(parents=True)

    script_path = scripts_root / "service_sample.py"
    script_path.write_text(
        """
from typing import Annotated

from pcontext import Image, Param, Service

service = Service()


@service(
    title="Detector service",
    timeout=120,
    max_downtime=30,
    on_startup=True,
)
class Detector:
    def __init__(
        self,
        threshold: Annotated[float, Param(default=0.5, ge=0.0, le=1.0)],
    ) -> None:
        self.threshold = threshold

    @service.script(
        title="Detect on image",
        timeout=5,
    )
    def detect(
        self,
        image_path: Annotated[str, Image()],
    ) -> None:
        return None
""",
        encoding="utf-8",
    )

    result = inspect_script_file(script_path, scripts_root=scripts_root)

    assert len(result.oneshot_scripts) == 0
    assert len(result.services) == 1

    service_manifest = result.services[0]
    assert service_manifest.title == "Detector service"
    assert service_manifest.on_startup is True
    assert len(service_manifest.init_params) == 1
    assert len(service_manifest.scripts) == 1

    method_manifest = service_manifest.scripts[0]
    assert method_manifest.title == "Detect on image"
    assert method_manifest.service_id == service_manifest.id
    assert len(method_manifest.inputs) == 1
    assert method_manifest.supports_direct_run is False
