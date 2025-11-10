"""Fixture module defining service and service scripts."""

from contextipy import service, service_script

ICON = "🛠"
CATEGORIES = ("service", "test")


@service(
    service_id="example_service",
    title="Example Service",
    description="Service used in tests",
)
def example_service() -> str:
    """Service docstring."""
    return "service"


@service_script(
    script_id="service_script_example",
    service_id="example_service",
    title="Service Script",
    description="A script that uses the example service",
    accepts=("text",),
)
def run_service_script(text: str) -> str:
    """Process text using the service."""
    return text.upper()
