from __future__ import annotations

from pathlib import Path

from pcontext.config import get_paths
from pcontext.registrar.registration import register_scripts
from pcontext.storage.state import StateStore


def test_register_scripts_saves_registration_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    """
    Регистрация должна сохранять снимок файла в SQLite
    и считать новый venv корректно созданным.
    """
    home_dir = tmp_path / ".pcontext"
    paths = get_paths(home_dir)
    paths.scripts.mkdir(parents=True, exist_ok=True)

    script_path = paths.scripts / "sample.py"
    script_path.write_text(
        '''
"""
requests>=2.31
"""
from typing import Annotated
from pcontext import Image, oneshot_script

@oneshot_script(
    id="script.sample",
    title="Sample",
)
def run(image_path: Annotated[str, Image()]) -> None:
    return None
''',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "pcontext.registrar.registration.ensure_shared_venv",
        lambda _paths: type(
            "FakeSharedVenvInfo",
            (),
            {"python_executable": "python", "created": True},
        )(),
    )

    installed_groups: list[list[str]] = []
    monkeypatch.setattr(
        "pcontext.registrar.registration.install_requirements",
        lambda _paths, requirements: installed_groups.append(list(requirements)),
    )

    inspected_files: list[str] = []
    monkeypatch.setattr(
        "pcontext.registrar.registration.inspect_script_file_in_subprocess",
        lambda file_path, scripts_root: inspected_files.append(str(file_path)),
    )

    state_store = StateStore(paths.state_db)
    result = register_scripts(paths, state_store=state_store)

    assert result.processed_files == 1
    assert result.changed_files == 1
    assert result.failed_files == 0
    assert result.venv_created is True
    assert installed_groups == [["requests>=2.31"]]
    assert inspected_files == [str(script_path)]

    snapshots = state_store.list_registration_modules()
    assert len(snapshots) == 1
    assert snapshots[0].relative_path == "sample.py"
    assert snapshots[0].status == "registered"
    assert snapshots[0].dependencies == ["requests>=2.31"]


def test_register_scripts_skips_unchanged_file(monkeypatch, tmp_path: Path) -> None:
    """
    Если файл не изменился и venv уже существует, регистрация должна его пропустить.
    """
    home_dir = tmp_path / ".pcontext"
    paths = get_paths(home_dir)
    paths.scripts.mkdir(parents=True, exist_ok=True)

    script_path = paths.scripts / "sample.py"
    script_path.write_text(
        """
from typing import Annotated
from pcontext import Image, oneshot_script

@oneshot_script(
    id="script.sample",
    title="Sample",
)
def run(image_path: Annotated[str, Image()]) -> None:
    return None
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "pcontext.registrar.registration.ensure_shared_venv",
        lambda _paths: type(
            "FakeSharedVenvInfo",
            (),
            {"python_executable": "python", "created": False},
        )(),
    )

    monkeypatch.setattr(
        "pcontext.registrar.registration.install_requirements",
        lambda _paths, requirements: None,
    )
    monkeypatch.setattr(
        "pcontext.registrar.registration.inspect_script_file_in_subprocess",
        lambda file_path, scripts_root: None,
    )

    state_store = StateStore(paths.state_db)

    first_result = register_scripts(paths, state_store=state_store)
    assert first_result.changed_files == 1

    second_result = register_scripts(paths, state_store=state_store)
    assert second_result.unchanged_files == 1
    assert second_result.changed_files == 0
