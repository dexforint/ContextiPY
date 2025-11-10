"""Runtime execution utilities for Contextipy.

This package contains:

- **script_runner**: Launch oneshot scripts in isolated subprocesses
- **service_manager**: Manage long-running service processes
- **context_entry**: Entry point for context menu script execution
- **action_handler**: Execute actions returned by scripts
"""

from .action_handler import ActionHandler, ActionResult
from .context_entry import ContextEntryCoordinator, ContextEntryError, parse_arguments
from .script_runner import (
    DefaultEventHook as ScriptDefaultEventHook,
    ScriptEventHook,
    ScriptInput,
    ScriptResult,
    ScriptRunner,
    create_script_runner,
)
from .service_manager import (
    DefaultServiceEventHook,
    ServiceEventHook,
    ServiceInfo,
    ServiceManager,
    ServiceRequest,
    ServiceResponse,
    ServiceState,
    create_service_manager,
)

__all__ = [
    "ActionHandler",
    "ActionResult",
    "ScriptRunner",
    "ScriptInput",
    "ScriptResult",
    "ScriptEventHook",
    "ScriptDefaultEventHook",
    "create_script_runner",
    "ServiceManager",
    "ServiceState",
    "ServiceInfo",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceEventHook",
    "DefaultServiceEventHook",
    "create_service_manager",
    "ContextEntryCoordinator",
    "ContextEntryError",
    "parse_arguments",
]
