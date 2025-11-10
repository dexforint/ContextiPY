"""A simple oneshot script example demonstrating basic script creation.

This script shows the fundamental structure of a Contextipy oneshot script,
including decorator usage, action returns, and docstring documentation.

```requirements
# No external dependencies required for this example.
```
"""

from typing import Sequence

from contextipy import oneshot_script
from contextipy.actions import Action, Notify, Text


@oneshot_script(
    script_id="hello_world",
    title="Hello World",
    description="Display a friendly greeting message",
    icon="👋",
    categories=["examples", "greeting"],
)
def hello_world() -> Sequence[Action]:
    """Execute the hello world script.

    This simple script demonstrates how to return multiple actions from
    a oneshot script. Actions are the primary way scripts interact with
    the user and system.

    Returns:
        A list of actions: a notification and text output.
    """
    return [
        Notify(title="Hello!", message="Welcome to Contextipy"),
        Text(content="Hello, World! This is your first Contextipy script."),
    ]
