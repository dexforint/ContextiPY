"""Unit tests for question schemas, validation, and Ask API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

import pytest

from contextipy.questions import Ask, Question, Questions
from contextipy.questions.models import QuestionDefinition
from contextipy.questions.types import ImageQuery


class Colour(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@dataclass
class ProfileQuestions(Questions):
    name: Annotated[str, Question(title="Full name", description="Your complete name")]
    age: Annotated[int, Question(title="Age", ge=18, le=120)]
    favorite_colour: Annotated[
        Colour,
        Question(title="Favourite colour", enum=[Colour.RED, Colour.GREEN, Colour.BLUE]),
    ] = Colour.RED
    avatar: Annotated[
        Path | None,
        ImageQuery(title="Profile picture", required=False, description="Optional avatar image"),
    ] = None


def test_definitions_extract_schema() -> None:
    definitions = ProfileQuestions.definitions()
    assert len(definitions) == 4

    names = [definition.name for definition in definitions]
    assert names == ["name", "age", "favorite_colour", "avatar"]

    age_definition = next(defn for defn in definitions if defn.name == "age")
    assert isinstance(age_definition, QuestionDefinition)
    assert age_definition.required is True
    assert age_definition.question.ge == 18
    assert age_definition.question.le == 120

    colour_definition = next(defn for defn in definitions if defn.name == "favorite_colour")
    assert colour_definition.required is False
    assert colour_definition.has_default() is True
    assert colour_definition.default == Colour.RED

    avatar_definition = next(defn for defn in definitions if defn.name == "avatar")
    assert avatar_definition.required is False
    assert avatar_definition.has_default() is False


def test_ui_schema_serialisation() -> None:
    schema = ProfileQuestions.ui_schema()
    assert len(schema) == 4

    age_schema = next(item for item in schema if item["name"] == "age")
    assert age_schema["title"] == "Age"
    assert age_schema["required"] is True
    assert age_schema["ge"] == 18
    assert age_schema["le"] == 120

    colour_schema = next(item for item in schema if item["name"] == "favorite_colour")
    assert colour_schema["enum"] == ["Colour.RED", "Colour.GREEN", "Colour.BLUE"]

    avatar_schema = next(item for item in schema if item["name"] == "avatar")
    assert avatar_schema["required"] is False
    assert avatar_schema["kind"] == "image"
    assert "formats" in avatar_schema


def test_validate_answers_success() -> None:
    answers = {
        "name": "Alice",
        "age": 30,
        "favorite_colour": "GREEN",
        "avatar": "/tmp/avatar.png",
    }

    validated = ProfileQuestions.validate_answers(answers)
    assert validated["name"] == "Alice"
    assert validated["age"] == 30
    assert validated["favorite_colour"] == Colour.GREEN
    assert validated["avatar"] == Path("/tmp/avatar.png")


def test_validate_answers_uses_defaults() -> None:
    answers = {
        "name": "Bob",
        "age": 45,
    }

    validated = ProfileQuestions.validate_answers(answers)
    assert validated["favorite_colour"] == Colour.RED
    assert validated["avatar"] is None


def test_validate_answers_enforces_bounds() -> None:
    answers = {
        "name": "Charlie",
        "age": 10,
        "favorite_colour": Colour.BLUE,
    }

    with pytest.raises(ValueError, match="must be >= 18"):
        ProfileQuestions.validate_answers(answers)


def test_validate_answers_enforces_enum() -> None:
    answers = {
        "name": "Dana",
        "age": 28,
        "favorite_colour": "PURPLE",
    }

    with pytest.raises(TypeError):
        ProfileQuestions.validate_answers(answers)


def test_validate_answers_missing_required_field() -> None:
    answers = {
        "age": 30,
        "favorite_colour": Colour.GREEN,
    }

    with pytest.raises(ValueError, match="requires a value"):
        ProfileQuestions.validate_answers(answers)


def test_from_answers_creates_dataclass() -> None:
    answers = {
        "name": "Eve",
        "age": 38,
        "favorite_colour": Colour.BLUE,
        "avatar": None,
    }

    result = ProfileQuestions.from_answers(answers)
    assert isinstance(result, ProfileQuestions)
    assert result.name == "Eve"
    assert result.favorite_colour == Colour.BLUE
    assert result.avatar is None


def test_ask_returns_instance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    answers = {
        "name": "Fred",
        "age": 26,
        "favorite_colour": "GREEN",
        "avatar": str(tmp_path / "avatar.png"),
    }

    def fake_ask(schema: list[dict[str, str]]) -> dict[str, str]:
        return answers

    monkeypatch.setattr("contextipy.questions.ui.ask", fake_ask)

    result = Ask(ProfileQuestions)
    assert isinstance(result, ProfileQuestions)
    assert result.name == "Fred"
    assert result.favorite_colour == Colour.GREEN
    assert result.avatar == tmp_path / "avatar.png"


def test_ask_returns_none_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("contextipy.questions.ui.ask", lambda schema: None)
    assert Ask(ProfileQuestions) is None


def test_ask_requires_questions_subclass() -> None:
    with pytest.raises(TypeError):
        Ask(object)  # type: ignore[arg-type]


class NotADataclass(Questions):
    value: Annotated[int, Question(title="Value")]


def test_definitions_require_dataclass() -> None:
    with pytest.raises(TypeError, match="must be defined as dataclasses"):
        NotADataclass.definitions()
