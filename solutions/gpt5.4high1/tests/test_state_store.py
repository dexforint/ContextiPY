from __future__ import annotations

from pathlib import Path

from pcontext.storage.state import StateStore


def test_state_store_persists_parameter_values(tmp_path: Path) -> None:
    """
    Переопределённые значения параметров должны сохраняться между экземплярами StateStore.
    """
    db_path = tmp_path / "state.db"

    store_one = StateStore(db_path)
    store_one.set_parameter_value("script.demo", "quality", 95)
    store_one.set_parameter_value("script.demo", "enabled", True)

    store_two = StateStore(db_path)
    values = store_two.get_parameter_values("script.demo")

    assert values["quality"] == 95
    assert values["enabled"] is True


def test_state_store_reset_parameter_values(tmp_path: Path) -> None:
    """
    Должны работать сброс одного параметра и сброс всех параметров владельца.
    """
    db_path = tmp_path / "state.db"
    store = StateStore(db_path)

    store.set_parameter_value("script.demo", "a", 1)
    store.set_parameter_value("script.demo", "b", 2)

    removed_one = store.reset_parameter_value("script.demo", "a")
    assert removed_one is True
    assert "a" not in store.get_parameter_values("script.demo")

    removed_count = store.reset_all_parameter_values("script.demo")
    assert removed_count == 1
    assert store.get_parameter_values("script.demo") == {}


def test_state_store_writes_and_reads_run_logs(tmp_path: Path) -> None:
    """
    Записи лога должны сохраняться и читаться в обратном порядке по времени создания.
    """
    db_path = tmp_path / "state.db"
    store = StateStore(db_path)

    first_id = store.add_run_log(
        invocation_kind="oneshot_script",
        command_id="script.one",
        title="First",
        duration_ms=10,
        success=True,
        message="ok",
        action_json='{"kind":"none"}',
        context_json='{"source":"selection","current_folder":"C:/tmp","entries":[]}',
    )
    second_id = store.add_run_log(
        invocation_kind="service_script",
        command_id="service.two.run",
        title="Second",
        duration_ms=None,
        success=False,
        message="boom",
        action_json=None,
        context_json=None,
    )

    logs = store.list_run_logs(limit=10)

    assert logs[0].log_id == second_id
    assert logs[1].log_id == first_id

    second = store.get_run_log(second_id)
    assert second is not None
    assert second.success is False
    assert second.title == "Second"
