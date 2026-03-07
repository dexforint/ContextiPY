from __future__ import annotations

from pcontext.agent.catalog import AgentCatalog
from pcontext.storage.models import ParameterValueView
from pcontext.storage.state import StateStore


def build_parameter_views(
    catalog: AgentCatalog,
    state_store: StateStore,
) -> list[ParameterValueView]:
    """
    Собирает плоский список всех параметров из текущего каталога.

    Этот вид удобен и для CLI, и для будущего окна настройки параметров.
    """
    views: list[ParameterValueView] = []

    for script in catalog.oneshot_scripts:
        saved_values = state_store.get_parameter_values(script.id)
        for parameter in script.params:
            has_override = parameter.name in saved_values
            current_value = saved_values.get(parameter.name, parameter.default)
            views.append(
                ParameterValueView(
                    owner_kind="oneshot_script",
                    owner_id=script.id,
                    owner_title=script.title,
                    param_name=parameter.name,
                    default_value=parameter.default,
                    current_value=current_value,
                    has_override=has_override,
                )
            )

    for service in catalog.services:
        saved_service_values = state_store.get_parameter_values(service.id)
        for parameter in service.init_params:
            has_override = parameter.name in saved_service_values
            current_value = saved_service_values.get(parameter.name, parameter.default)
            views.append(
                ParameterValueView(
                    owner_kind="service",
                    owner_id=service.id,
                    owner_title=service.title,
                    param_name=parameter.name,
                    default_value=parameter.default,
                    current_value=current_value,
                    has_override=has_override,
                )
            )

        for method in service.scripts:
            saved_method_values = state_store.get_parameter_values(method.id)
            for parameter in method.params:
                has_override = parameter.name in saved_method_values
                current_value = saved_method_values.get(
                    parameter.name, parameter.default
                )
                views.append(
                    ParameterValueView(
                        owner_kind="service_script",
                        owner_id=method.id,
                        owner_title=method.title,
                        param_name=parameter.name,
                        default_value=parameter.default,
                        current_value=current_value,
                        has_override=has_override,
                    )
                )

    return sorted(
        views,
        key=lambda item: (
            item.owner_kind,
            item.owner_title.lower(),
            item.owner_id,
            item.param_name,
        ),
    )
