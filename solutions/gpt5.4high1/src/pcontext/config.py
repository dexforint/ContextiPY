from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PContextPaths:
    """
    Все основные пути приложения.

    Мы явно собираем их в один объект, чтобы не размазывать логику по проекту
    и упростить тестирование.
    """

    home: Path
    scripts: Path
    icons: Path
    venv: Path
    manifests: Path
    runtime: Path
    state_db: Path
    log_file: Path
    agent_endpoint: Path

    def as_dict(self) -> dict[str, str]:
        """
        Удобное строковое представление для CLI и отладки.
        """
        return {
            "home": str(self.home),
            "scripts": str(self.scripts),
            "icons": str(self.icons),
            "venv": str(self.venv),
            "manifests": str(self.manifests),
            "runtime": str(self.runtime),
            "state_db": str(self.state_db),
            "log_file": str(self.log_file),
            "agent_endpoint": str(self.agent_endpoint),
        }


def get_paths(base_dir: Path | None = None) -> PContextPaths:
    """
    Возвращает набор стандартных путей приложения.

    По умолчанию базовая директория — `~/.pcontext`.
    """
    home_dir = base_dir if base_dir is not None else Path.home() / ".pcontext"

    return PContextPaths(
        home=home_dir,
        scripts=home_dir / "scripts",
        icons=home_dir / "icons",
        venv=home_dir / "venv",
        manifests=home_dir / "manifests",
        runtime=home_dir / "runtime",
        state_db=home_dir / "state.db",
        log_file=home_dir / "pcontext.log",
        agent_endpoint=home_dir / "runtime" / "agent-endpoint.json",
    )


def ensure_directories(paths: PContextPaths) -> None:
    """
    Создаёт все необходимые директории, если их ещё нет.
    """
    directories = (
        paths.home,
        paths.scripts,
        paths.icons,
        paths.venv,
        paths.manifests,
        paths.runtime,
    )

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
