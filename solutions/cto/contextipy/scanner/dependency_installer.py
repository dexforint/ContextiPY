"""Dependency installer for script requirements with caching and retry logic."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InstallStatus(Enum):
    """Status of a dependency installation."""

    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class InstallResult:
    """Result of a dependency installation attempt."""

    status: InstallStatus
    requirements: tuple[str, ...]
    stdout: str
    stderr: str
    error_message: str | None = None

    def successful(self) -> bool:
        return self.status in (InstallStatus.SUCCESS, InstallStatus.CACHED, InstallStatus.SKIPPED)


@dataclass
class InstallConfig:
    """Configuration for dependency installation."""

    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    timeout: float = 300.0
    pip_args: tuple[str, ...] = ()


def parse_requirements_from_docstring(docstring: str | None) -> tuple[str, ...]:
    """Extract requirements declared in a script docstring.

    The parser supports two formats:

    1. A dedicated section introduced by ``Requirements:`` followed by one
       requirement per line (optionally indented or listed with ``-``/``*``).
    2. A fenced Markdown block labelled ``requirements``.

    Requirement lines may include inline comments (``# comment``), which are
    ignored. Duplicate requirements are removed while preserving order.
    """

    if not docstring:
        return ()

    lines = docstring.splitlines()
    requirements: list[str] = []
    idx = 0
    total = len(lines)

    while idx < total:
        line = lines[idx]
        stripped = line.strip()
        lower = stripped.lower()

        # Fenced code block: ```requirements
        if stripped.startswith("```"):
            fence_lang = stripped[3:].strip().lower()
            idx += 1
            in_requirements_block = fence_lang.startswith("requirements")
            while idx < total:
                block_line = lines[idx].strip()
                if block_line.startswith("```"):
                    idx += 1
                    break
                if in_requirements_block:
                    requirement = _normalise_requirement_line(lines[idx])
                    if requirement:
                        requirements.append(requirement)
                idx += 1
            continue

        if lower.startswith("requirements:"):
            tail = line.split(":", 1)[1].strip()
            if tail:
                requirement = _normalise_requirement_line(tail)
                if requirement:
                    requirements.append(requirement)
            idx += 1
            collected, idx = _collect_requirement_block(lines, idx)
            requirements.extend(collected)
            continue

        idx += 1

    # De-duplicate while preserving order
    seen = dict.fromkeys(requirements)
    return tuple(seen)


def _collect_requirement_block(lines: list[str], start: int) -> tuple[list[str], int]:
    collected: list[str] = []
    idx = start
    total = len(lines)

    while idx < total:
        raw_line = lines[idx]
        stripped = raw_line.strip()
        if not stripped:
            idx += 1
            break
        if not raw_line.startswith((" ", "\t")) and not stripped.startswith(("-", "*")):
            # Stop if the next section starts (e.g. "Notes:")
            if ":" in stripped:
                break
        requirement = _normalise_requirement_line(raw_line)
        if not requirement:
            idx += 1
            continue
        collected.append(requirement)
        idx += 1

    return collected, idx


def _normalise_requirement_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith(("-", "*")):
        stripped = stripped[1:].strip()
    if stripped.startswith("#"):
        return ""
    if " #" in stripped:
        stripped = stripped.split(" #", 1)[0].rstrip()
    return stripped


def compute_requirements_hash(requirements: tuple[str, ...]) -> str:
    """Compute a stable hash for a sequence of requirements."""

    content = "\n".join(sorted(requirements))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class VenvStrategy(ABC):
    """Strategy interface for resolving virtual environments."""

    @abstractmethod
    def get_venv_path(self, script_id: str) -> Path:
        """Return the virtual environment path for ``script_id``."""

    @abstractmethod
    def get_pip_executable(self, script_id: str) -> Path:
        """Return the pip executable for ``script_id``."""

    @abstractmethod
    def ensure_venv_exists(self, script_id: str) -> None:
        """Create the virtual environment if it does not yet exist."""


class SharedVenvStrategy(VenvStrategy):
    """Virtual environment strategy sharing a single environment."""

    def __init__(self, venv_path: Path) -> None:
        self._venv_path = venv_path

    def get_venv_path(self, script_id: str) -> Path:  # noqa: ARG002 - required by interface
        return self._venv_path

    def get_pip_executable(self, script_id: str) -> Path:  # noqa: ARG002 - interface
        pip_path = self._venv_path / "bin" / "pip"
        if pip_path.exists():
            return pip_path
        windows_pip = self._venv_path / "Scripts" / "pip.exe"
        if windows_pip.exists():
            return windows_pip
        return Path("pip")

    def ensure_venv_exists(self, script_id: str) -> None:  # noqa: ARG002 - interface
        if self._venv_path.exists():
            return
        logger.info("Creating shared virtual environment at %s", self._venv_path)
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(self._venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )


class PerScriptVenvStrategy(VenvStrategy):
    """Virtual environment strategy isolating each script in its own venv."""

    def __init__(self, venv_root: Path) -> None:
        self._venv_root = venv_root

    def get_venv_path(self, script_id: str) -> Path:
        return self._venv_root / script_id

    def get_pip_executable(self, script_id: str) -> Path:
        venv_path = self.get_venv_path(script_id)
        pip_path = venv_path / "bin" / "pip"
        if pip_path.exists():
            return pip_path
        windows_pip = venv_path / "Scripts" / "pip.exe"
        if windows_pip.exists():
            return windows_pip
        return Path("pip")

    def ensure_venv_exists(self, script_id: str) -> None:
        venv_path = self.get_venv_path(script_id)
        if venv_path.exists():
            return
        logger.info("Creating virtual environment for %s at %s", script_id, venv_path)
        venv_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )


class DependencyInstaller:
    """Install dependencies for scripts with caching and retry support."""

    def __init__(
        self,
        strategy: VenvStrategy,
        cache_dir: Path | None = None,
        config: InstallConfig | None = None,
    ) -> None:
        self._strategy = strategy
        self._cache_dir = cache_dir or Path.home() / ".contextipy" / "dep_cache"
        self._config = config or InstallConfig()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def install_requirements(
        self,
        script_id: str,
        requirements: tuple[str, ...],
    ) -> InstallResult:
        if not requirements:
            logger.debug("No requirements declared for script %s", script_id)
            return InstallResult(InstallStatus.SKIPPED, (), "", "")

        req_hash = compute_requirements_hash(requirements)
        if self._is_cached(script_id, req_hash):
            logger.info("Dependencies for %s already satisfied (cache hit)", script_id)
            return InstallResult(InstallStatus.CACHED, requirements, "", "")

        try:
            self._strategy.ensure_venv_exists(script_id)
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to create virtual environment for %s", script_id)
            return InstallResult(
                InstallStatus.FAILED,
                requirements,
                exc.output or "",
                exc.stderr or "",
                error_message="Virtual environment creation failed",
            )
        except OSError as exc:
            logger.error("Error creating virtual environment for %s: %s", script_id, exc)
            return InstallResult(InstallStatus.FAILED, requirements, "", "", str(exc))

        last_result: InstallResult | None = None
        delay = self._config.retry_delay

        for attempt in range(1, self._config.max_retries + 1):
            try:
                result = self._install_with_pip(script_id, requirements)
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                error_message = (
                    f"pip install timed out after {self._config.timeout} seconds"
                )
                result = InstallResult(InstallStatus.FAILED, requirements, stdout, stderr, error_message)

            if result.status is InstallStatus.SUCCESS:
                self._mark_cached(script_id, req_hash, requirements)
                logger.info("Installed dependencies for %s on attempt %d", script_id, attempt)
                return result

            last_result = result
            logger.warning(
                "Failed to install dependencies for %s on attempt %d/%d: %s",
                script_id,
                attempt,
                self._config.max_retries,
                result.error_message or "unknown error",
            )

            if attempt < self._config.max_retries:
                time.sleep(delay)
                delay *= self._config.backoff_multiplier

        if last_result is None:
            last_result = InstallResult(InstallStatus.FAILED, requirements, "", "", "Installation failed")
        return last_result

    def _install_with_pip(
        self,
        script_id: str,
        requirements: tuple[str, ...],
    ) -> InstallResult:
        pip_executable = self._strategy.get_pip_executable(script_id)
        command = [str(pip_executable), "install", *self._config.pip_args, *requirements]

        logger.debug("Running pip for %s: %s", script_id, " ".join(command))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                timeout=self._config.timeout,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            return InstallResult(InstallStatus.FAILED, requirements, "", "", str(exc))

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        if completed.returncode == 0:
            return InstallResult(InstallStatus.SUCCESS, requirements, stdout, stderr)

        error_message = f"pip exited with status {completed.returncode}"
        return InstallResult(InstallStatus.FAILED, requirements, stdout, stderr, error_message)

    def _is_cached(self, script_id: str, req_hash: str) -> bool:
        cache_file = self._cache_dir / f"{script_id}.json"
        if not cache_file.exists():
            return False
        try:
            with cache_file.open("r", encoding="utf-8") as cache_fp:
                payload = json.load(cache_fp)
        except (OSError, json.JSONDecodeError):
            return False
        return payload.get("requirements_hash") == req_hash

    def _mark_cached(
        self,
        script_id: str,
        req_hash: str,
        requirements: tuple[str, ...],
    ) -> None:
        cache_file = self._cache_dir / f"{script_id}.json"
        payload: dict[str, Any] = {
            "requirements_hash": req_hash,
            "requirements": list(requirements),
            "installed_at": time.time(),
        }
        try:
            with cache_file.open("w", encoding="utf-8") as cache_fp:
                json.dump(payload, cache_fp, indent=2)
        except OSError as exc:
            logger.warning("Unable to persist dependency cache for %s: %s", script_id, exc)

    def clear_cache(self, script_id: str | None = None) -> None:
        if script_id is None:
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)
            logger.info("Cleared dependency installer cache")
            return

        cache_file = self._cache_dir / f"{script_id}.json"
        cache_file.unlink(missing_ok=True)
        logger.info("Cleared dependency installer cache for %s", script_id)


__all__ = [
    "DependencyInstaller",
    "InstallConfig",
    "InstallResult",
    "InstallStatus",
    "PerScriptVenvStrategy",
    "SharedVenvStrategy",
    "VenvStrategy",
    "compute_requirements_hash",
    "parse_requirements_from_docstring",
]
