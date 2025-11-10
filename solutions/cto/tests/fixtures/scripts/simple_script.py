"""Simple test script for scanner testing."""

from contextipy import oneshot_script

__icon__ = "⚡"
__categories__ = ["test", "simple"]


@oneshot_script(
    script_id="simple_test",
    title="Simple Test Script",
    description="A simple test script for scanning",
)
def simple_script() -> str:
    """Execute a simple test script.
    
    This is a docstring for testing purposes.
    """
    return "success"
