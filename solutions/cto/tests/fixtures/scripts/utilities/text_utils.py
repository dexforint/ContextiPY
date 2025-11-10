"""Text utility scripts for testing grouping."""

from contextipy import Text, oneshot_script


@oneshot_script(
    script_id="text_to_upper",
    title="Text to Upper",
    description="Converts text to uppercase",
    accepts=[Text],
)
def to_upper(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


@oneshot_script(
    script_id="text_to_lower",
    title="Text to Lower",
    description="Converts text to lowercase",
    accepts=[Text],
    timeout=5.0,
)
def to_lower(text: str) -> str:
    """Convert text to lowercase."""
    return text.lower()
