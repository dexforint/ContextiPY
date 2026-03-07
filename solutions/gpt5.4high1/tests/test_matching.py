from __future__ import annotations

from pcontext.agent.mock_registry import DemoRegistry
from pcontext.runtime.ipc_models import ShellContext, ShellEntry
from pcontext.runtime.matching import matches_input_expression
from pcontext.runtime.shell import normalize_shell_context
from pcontext.sdk.inputs import CurrentFolder, Image, Images, Video


def test_single_image_matches_image_rule() -> None:
    """
    Один выбранный png-файл должен подходить под Image(),
    но не должен подходить под Video().
    """
    context = ShellContext(
        source="selection",
        current_folder="/tmp",
        entries=[
            ShellEntry(
                path="/tmp/picture.png",
                entry_type="file",
            )
        ],
    )

    normalized = normalize_shell_context(context)

    assert matches_input_expression(Image(), normalized) is True
    assert matches_input_expression(Video(), normalized) is False


def test_background_matches_current_folder_rule() -> None:
    """
    Клик по пустой области папки должен подходить под CurrentFolder().
    """
    context = ShellContext(
        source="background",
        current_folder="/tmp",
        entries=[],
    )

    normalized = normalize_shell_context(context)

    assert matches_input_expression(CurrentFolder(), normalized) is True


def test_demo_service_item_is_hidden_until_service_is_running() -> None:
    """
    Пункт демо-сервиса должен появляться только после включения сервиса.
    """
    context = ShellContext(
        source="selection",
        current_folder="/tmp",
        entries=[
            ShellEntry(
                path="/tmp/image.jpg",
                entry_type="file",
            )
        ],
    )

    normalized = normalize_shell_context(context)
    registry = DemoRegistry()

    titles_before = [item.title for item in registry.list_menu_items(normalized)]
    assert "Demo: YOLO detect" not in titles_before

    registry.set_service_state("demo_yolo", True)

    titles_after = [item.title for item in registry.list_menu_items(normalized)]
    assert "Demo: YOLO detect" in titles_after


def test_images_rule_requires_all_selected_files_to_be_images() -> None:
    """
    Для Images() все выбранные объекты должны быть изображениями.
    """
    valid_context = ShellContext(
        source="selection",
        current_folder="/tmp",
        entries=[
            ShellEntry(path="/tmp/1.png", entry_type="file"),
            ShellEntry(path="/tmp/2.jpg", entry_type="file"),
        ],
    )
    invalid_context = ShellContext(
        source="selection",
        current_folder="/tmp",
        entries=[
            ShellEntry(path="/tmp/1.png", entry_type="file"),
            ShellEntry(path="/tmp/readme.txt", entry_type="file"),
        ],
    )

    assert (
        matches_input_expression(Images(), normalize_shell_context(valid_context))
        is True
    )
    assert (
        matches_input_expression(Images(), normalize_shell_context(invalid_context))
        is False
    )
