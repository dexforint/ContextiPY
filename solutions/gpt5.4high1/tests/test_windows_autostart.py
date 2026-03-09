from __future__ import annotations

from pathlib import Path

from pcontext.platform.windows.autostart import build_windows_gui_launch_command


def test_build_windows_gui_launch_command_prefers_pythonw(
    monkeypatch, tmp_path: Path
) -> None:
    scripts_dir = tmp_path / "Scripts"
    scripts_dir.mkdir(parents=True)

    python_exe = scripts_dir / "python.exe"
    pythonw_exe = scripts_dir / "pythonw.exe"

    python_exe.write_text("", encoding="utf-8")
    pythonw_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr("sys.executable", str(python_exe))

    command = build_windows_gui_launch_command(hidden=True)

    assert "pythonw.exe" in command.lower()
    assert "-m pcontext.cli gui --hidden" in command


def test_build_windows_gui_launch_command_for_packaged_gui(
    monkeypatch, tmp_path: Path
) -> None:
    gui_exe = tmp_path / "pcontext-gui.exe"
    gui_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr("sys.executable", str(gui_exe))

    command = build_windows_gui_launch_command(hidden=True)

    assert "pcontext-gui.exe" in command.lower()
    assert "--hidden" in command
    assert " gui " not in command.lower()
