from __future__ import annotations

from pathlib import Path

from pcontext.storage.state import StateStore


def test_list_command_usage_stats_aggregates_real_script_runs(tmp_path: Path) -> None:
    """
    Статистика использования должна считать только реальные script/service_script запуски.
    """
    store = StateStore(tmp_path / "state.db")

    store.add_run_log(
        invocation_kind="oneshot_script",
        command_id="script.a",
        title="A",
        duration_ms=10,
        success=True,
        message="ok",
        action_json=None,
        context_json=None,
    )
    store.add_run_log(
        invocation_kind="service_script",
        command_id="script.a",
        title="A",
        duration_ms=12,
        success=True,
        message="ok2",
        action_json=None,
        context_json=None,
    )
    store.add_run_log(
        invocation_kind="launcher",
        command_id="windows_launcher.selection_show_menu",
        title="Launcher",
        duration_ms=None,
        success=True,
        message="launcher",
        action_json=None,
        context_json=None,
    )

    stats = store.list_command_usage_stats(
        ["script.a", "windows_launcher.selection_show_menu"]
    )

    assert stats["script.a"].launch_count == 2
    assert stats["script.a"].last_used_utc is not None
    assert "windows_launcher.selection_show_menu" not in stats
