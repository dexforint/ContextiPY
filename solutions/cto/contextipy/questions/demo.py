"""Demo script showing Ask dialog usage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

from contextipy.questions import Ask, Question, Questions
from contextipy.questions.types import ImageQuery


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TaskQuestions(Questions):
    """Example questions for creating a task."""
    
    task_name: Annotated[str, Question(title="Task Name", description="Enter the task name")]
    priority: Annotated[
        Priority,
        Question(title="Priority", enum=[Priority.LOW, Priority.MEDIUM, Priority.HIGH]),
    ] = Priority.MEDIUM
    estimated_hours: Annotated[
        float,
        Question(title="Estimated Hours", ge=0.5, le=40.0, description="Time to complete"),
    ]
    notes: Annotated[
        str | None,
        Question(title="Additional Notes", required=False, description="Optional notes"),
    ] = None
    attachment: Annotated[
        Path | None,
        ImageQuery(title="Attachment", required=False, description="Optional screenshot"),
    ] = None


def demo_ask_dialog() -> None:
    """Demonstrate the Ask dialog in action."""
    from contextipy.ui import ensure_application
    
    # Ensure QApplication is initialized
    app = ensure_application()
    
    # Ask the user for information
    result = Ask(TaskQuestions)
    
    if result is None:
        print("User cancelled the dialog")
        return
    
    # Use the results
    print(f"Task created:")
    print(f"  Name: {result.task_name}")
    print(f"  Priority: {result.priority.value}")
    print(f"  Estimated Hours: {result.estimated_hours}")
    if result.notes:
        print(f"  Notes: {result.notes}")
    if result.attachment:
        print(f"  Attachment: {result.attachment}")


if __name__ == "__main__":
    demo_ask_dialog()
