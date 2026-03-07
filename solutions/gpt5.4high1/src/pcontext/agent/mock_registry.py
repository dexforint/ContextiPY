from __future__ import annotations

import threading
from dataclasses import dataclass

from pcontext.runtime.matching import (
    MenuCommandDefinition,
    build_visible_menu_items,
    matches_input_expression,
)
from pcontext.runtime.shell import InvocationContext
from pcontext.sdk.inputs import CurrentFolder, File, Image, Images


@dataclass(frozen=True, slots=True)
class MenuInvocationResult:
    """
    Результат демонстрационного запуска пункта меню.
    """

    accepted: bool
    message: str


class ServiceStateStore:
    """
    Потокобезопасное хранилище состояний сервисов.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, bool] = {
            "demo_yolo": False,
        }

    def is_running(self, service_name: str) -> bool:
        """
        Возвращает текущее состояние сервиса.
        """
        with self._lock:
            return self._states.get(service_name, False)

    def set_running(self, service_name: str, running: bool) -> None:
        """
        Обновляет состояние сервиса.
        """
        with self._lock:
            self._states[service_name] = running


class DemoRegistry:
    """
    Временный демонстрационный реестр команд.

    Он нужен только для vertical slice:
    Explorer/Nautilus должны уже сейчас уметь запрашивать у агента
    динамический список пунктов меню, даже до подключения настоящего регистратора.
    """

    def __init__(self) -> None:
        self._service_states = ServiceStateStore()
        self._commands: tuple[MenuCommandDefinition, ...] = (
            MenuCommandDefinition(
                id="demo.show_single_file",
                title="Demo: show selected file",
                input_expression=File(),
            ),
            MenuCommandDefinition(
                id="demo.batch_images",
                title="Demo: batch images",
                input_expression=Images(),
            ),
            MenuCommandDefinition(
                id="demo.current_folder",
                title="Demo: current folder",
                input_expression=CurrentFolder(),
            ),
            MenuCommandDefinition(
                id="demo.yolo_detect",
                title="Demo: YOLO detect",
                input_expression=Image(),
                service_name="demo_yolo",
            ),
        )

    def list_menu_items(self, context: InvocationContext) -> list[object]:
        """
        Возвращает список видимых пунктов меню для данного контекста.
        """
        return build_visible_menu_items(
            self._commands,
            context,
            is_service_running=self._service_states.is_running,
        )

    def set_service_state(self, service_name: str, running: bool) -> None:
        """
        Меняет состояние демо-сервиса.
        """
        self._service_states.set_running(service_name, running)

    def invoke(
        self, menu_item_id: str, context: InvocationContext
    ) -> MenuInvocationResult:
        """
        Выполняет демонстрационное действие.

        Здесь пока нет реального запуска Python-скриптов.
        На этом этапе нам важно проверить сам маршрут:
        shell -> агент -> проверка видимости -> выполнение команды.
        """
        command = next(
            (item for item in self._commands if item.id == menu_item_id), None
        )
        if command is None:
            return MenuInvocationResult(
                accepted=False,
                message=f"Пункт меню '{menu_item_id}' не найден.",
            )

        if command.service_name is not None and not self._service_states.is_running(
            command.service_name
        ):
            return MenuInvocationResult(
                accepted=False,
                message=(
                    f"Сервис '{command.service_name}' сейчас остановлен, "
                    "поэтому этот пункт меню недоступен."
                ),
            )

        if not matches_input_expression(command.input_expression, context):
            return MenuInvocationResult(
                accepted=False,
                message="Текущий контекст не подходит для этого пункта меню.",
            )

        selected_paths = [str(path) for path in context.selected_paths()]

        if menu_item_id == "demo.show_single_file":
            return MenuInvocationResult(
                accepted=True,
                message=f"Выбранный файл: {selected_paths[0]}",
            )

        if menu_item_id == "demo.batch_images":
            return MenuInvocationResult(
                accepted=True,
                message=f"Выбрано изображений: {len(selected_paths)}",
            )

        if menu_item_id == "demo.current_folder":
            return MenuInvocationResult(
                accepted=True,
                message=f"Текущая папка: {context.current_folder}",
            )

        if menu_item_id == "demo.yolo_detect":
            return MenuInvocationResult(
                accepted=True,
                message=f"YOLO обработал изображение: {selected_paths[0]}",
            )

        return MenuInvocationResult(
            accepted=False,
            message="Для этого пункта пока нет демонстрационного обработчика.",
        )
