"""Simple demo for testing the Ask dialog manually."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

from contextipy.questions import Ask, Question, Questions
from contextipy.questions.types import ImageQuery


class Size(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class SampleQuestions(Questions):
    """Sample questions demonstrating all widget types."""
    
    # Text input
    name: Annotated[str, Question(title="Your Name", description="Enter your full name")]
    
    # Integer with bounds
    age: Annotated[int, Question(title="Age", ge=18, le=120, description="Must be 18-120")]
    
    # Float with bounds
    rating: Annotated[float, Question(title="Rating", ge=0.0, le=5.0, description="Rate from 0.0 to 5.0")]
    
    # Enum with default
    size: Annotated[
        Size,
        Question(title="T-Shirt Size", enum=[Size.SMALL, Size.MEDIUM, Size.LARGE])
    ] = Size.MEDIUM
    
    # Optional text
    comments: Annotated[
        str | None,
        Question(title="Comments", required=False, description="Optional feedback")
    ] = None
    
    # Optional image
    photo: Annotated[
        Path | None,
        ImageQuery(title="Profile Photo", required=False, formats=["png", "jpg", "jpeg"])
    ] = None


def main() -> int:
    """Run the Ask dialog demo."""
    try:
        from contextipy.ui import ensure_application
    except ImportError:
        print("Error: PySide6 is not installed. Install it with: pip install PySide6")
        return 1
    
    print("Initializing Qt application...")
    app = ensure_application()
    
    print("Showing Ask dialog...")
    result = Ask(SampleQuestions)
    
    if result is None:
        print("\nUser cancelled the dialog")
        return 0
    
    print("\n=== ANSWERS ===")
    print(f"Name: {result.name}")
    print(f"Age: {result.age}")
    print(f"Rating: {result.rating}")
    print(f"Size: {result.size.value}")
    if result.comments:
        print(f"Comments: {result.comments}")
    if result.photo:
        print(f"Photo: {result.photo}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
