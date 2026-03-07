from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pcontext.registrar.models import InputRuleManifest
from pcontext.runtime.ipc_models import MenuItemDescriptor
from pcontext.runtime.shell import InvocationContext, SelectionEntry
from pcontext.sdk.inputs import InputSpec, SelectionExpression


@dataclass(frozen=True, slots=True)
class MenuCommandDefinition:
    """
    Минимальная декларация зарегистрированного пункта меню
    на этапе прямой работы с SDK-объектами.
    """

    id: str
    title: str
    input_expression: SelectionExpression
    service_name: str | None = None
    icon: str | None = None

    def to_menu_item(self) -> MenuItemDescriptor:
        """
        Преобразует внутреннюю декларацию в объект,
        который можно отдать shell-клиенту.
        """
        return MenuItemDescriptor(
            id=self.id,
            title=self.title,
            icon=self.icon,
            enabled=True,
        )


@dataclass(frozen=True, slots=True)
class ManifestMenuCommandDefinition:
    """
    Пункт меню, восстановленный из сериализованного манифеста регистратора.
    """

    id: str
    title: str
    input_rules: tuple[InputRuleManifest, ...]
    service_id: str | None = None
    icon: str | None = None

    def to_menu_item(self) -> MenuItemDescriptor:
        """
        Преобразует команду в IPC-объект для shell-клиента.
        """
        return MenuItemDescriptor(
            id=self.id,
            title=self.title,
            icon=self.icon,
            enabled=True,
        )


def _entry_matches_kind_extensions(
    entry: SelectionEntry,
    *,
    kind: str,
    extensions: Sequence[str],
) -> bool:
    """
    Проверяет, подходит ли один выбранный объект под правило вида
    `file`, `folder`, `image`, `extensions` и так далее.
    """
    if kind == "file":
        return entry.entry_type == "file"

    if kind == "folder":
        return entry.entry_type == "folder"

    if kind == "current_folder":
        return False

    if entry.entry_type != "file":
        return False

    if kind == "extensions":
        return entry.extension in extensions

    return entry.extension in extensions


def _entry_matches_spec(entry: SelectionEntry, spec: InputSpec) -> bool:
    """
    Проверяет, подходит ли один выбранный объект под одно атомарное правило SDK.
    """
    return _entry_matches_kind_extensions(
        entry,
        kind=spec.kind,
        extensions=spec.extensions,
    )


def _entry_matches_rule(entry: SelectionEntry, rule: InputRuleManifest) -> bool:
    """
    Проверяет, подходит ли один выбранный объект под одно правило из манифеста.
    """
    return _entry_matches_kind_extensions(
        entry,
        kind=rule.kind,
        extensions=rule.extensions,
    )


def _context_matches_spec(spec: InputSpec, context: InvocationContext) -> bool:
    """
    Проверяет, подходит ли весь контекст под одно атомарное правило SDK.
    """
    if spec.kind == "current_folder":
        return (
            context.source == "background"
            and context.current_folder is not None
            and not context.entries
        )

    if context.source != "selection":
        return False

    if spec.multiple:
        return bool(context.entries) and all(
            _entry_matches_spec(entry, spec) for entry in context.entries
        )

    return len(context.entries) == 1 and _entry_matches_spec(context.entries[0], spec)


def _context_matches_rule(rule: InputRuleManifest, context: InvocationContext) -> bool:
    """
    Проверяет, подходит ли весь контекст под одно правило из манифеста.
    """
    if rule.kind == "current_folder":
        return (
            context.source == "background"
            and context.current_folder is not None
            and not context.entries
        )

    if context.source != "selection":
        return False

    if rule.multiple:
        return bool(context.entries) and all(
            _entry_matches_rule(entry, rule) for entry in context.entries
        )

    return len(context.entries) == 1 and _entry_matches_rule(context.entries[0], rule)


def find_matching_input_spec(
    expression: SelectionExpression,
    context: InvocationContext,
) -> InputSpec | None:
    """
    Возвращает первое атомарное правило SDK, которое подходит под контекст.
    """
    for spec in expression.flatten():
        if _context_matches_spec(spec, context):
            return spec

    return None


def matches_input_expression(
    expression: SelectionExpression,
    context: InvocationContext,
) -> bool:
    """
    Проверяет выражение выбора целиком для SDK-объектов.
    """
    return find_matching_input_spec(expression, context) is not None


def matches_manifest_input_rules(
    rules: Sequence[InputRuleManifest],
    context: InvocationContext,
) -> bool:
    """
    Проверяет сериализованные правила выбора целиком.
    """
    return any(_context_matches_rule(rule, context) for rule in rules)


def build_visible_menu_items(
    commands: tuple[MenuCommandDefinition, ...],
    context: InvocationContext,
    *,
    is_service_running: Callable[[str], bool],
) -> list[MenuItemDescriptor]:
    """
    Собирает список пунктов меню для команд, описанных SDK-объектами.
    """
    visible_items: list[MenuItemDescriptor] = []

    for command in commands:
        if command.service_name is not None and not is_service_running(
            command.service_name
        ):
            continue

        if not matches_input_expression(command.input_expression, context):
            continue

        visible_items.append(command.to_menu_item())

    return visible_items


def build_visible_menu_items_from_manifest_commands(
    commands: tuple[ManifestMenuCommandDefinition, ...],
    context: InvocationContext,
    *,
    is_service_running: Callable[[str], bool],
) -> list[MenuItemDescriptor]:
    """
    Собирает список пунктов меню для команд, восстановленных из манифестов.
    """
    visible_items: list[MenuItemDescriptor] = []

    for command in commands:
        if command.service_id is not None and not is_service_running(
            command.service_id
        ):
            continue

        if not matches_manifest_input_rules(command.input_rules, context):
            continue

        visible_items.append(command.to_menu_item())

    return visible_items
