"""Unit tests for question validation edge cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import pytest

from contextipy.questions import Question, Questions


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class ValidationQuestions(Questions):
    score: Annotated[int, Question(title="Score", ge=0, le=100)]
    rating: Annotated[float, Question(title="Rating", ge=0.0, le=5.0)]
    category: Annotated[str, Question(title="Category", enum=["A", "B", "C"])]
    optional_field: Annotated[str | None, Question(title="Optional", required=False)]
    with_default: Annotated[int, Question(title="With default")] = 42


class TestNumericBounds:
    """Tests for numeric bound validation."""

    def test_integer_within_bounds(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 50, "rating": 3.5, "category": "A"}
        )
        assert result["score"] == 50

    def test_integer_at_lower_bound(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 0, "rating": 3.5, "category": "A"}
        )
        assert result["score"] == 0

    def test_integer_at_upper_bound(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 100, "rating": 3.5, "category": "A"}
        )
        assert result["score"] == 100

    def test_integer_below_lower_bound_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >= 0"):
            ValidationQuestions.validate_answers(
                {"score": -1, "rating": 3.5, "category": "A"}
            )

    def test_integer_above_upper_bound_raises(self) -> None:
        with pytest.raises(ValueError, match="must be <= 100"):
            ValidationQuestions.validate_answers(
                {"score": 101, "rating": 3.5, "category": "A"}
            )

    def test_float_within_bounds(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 75, "rating": 4.2, "category": "B"}
        )
        assert result["rating"] == 4.2

    def test_float_below_lower_bound_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >= 0.0"):
            ValidationQuestions.validate_answers(
                {"score": 75, "rating": -0.1, "category": "B"}
            )

    def test_float_above_upper_bound_raises(self) -> None:
        with pytest.raises(ValueError, match="must be <= 5.0"):
            ValidationQuestions.validate_answers(
                {"score": 75, "rating": 5.1, "category": "B"}
            )


class TestEnumValidation:
    """Tests for enum constraint validation."""

    def test_valid_enum_string_value(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 80, "rating": 4.0, "category": "A"}
        )
        assert result["category"] == "A"

    def test_invalid_enum_value_raises(self) -> None:
        with pytest.raises(ValueError, match="must be one of"):
            ValidationQuestions.validate_answers(
                {"score": 80, "rating": 4.0, "category": "D"}
            )

    def test_enum_type_member(self) -> None:
        @dataclass
        class EnumQuestions(Questions):
            priority: Annotated[
                Priority, Question(title="Priority", enum=[Priority.LOW, Priority.HIGH])
            ]

        result = EnumQuestions.validate_answers({"priority": Priority.LOW})
        assert result["priority"] == Priority.LOW

    def test_enum_by_name(self) -> None:
        @dataclass
        class EnumQuestions(Questions):
            priority: Annotated[Priority, Question(title="Priority")]

        result = EnumQuestions.validate_answers({"priority": "MEDIUM"})
        assert result["priority"] == Priority.MEDIUM

    def test_enum_by_value(self) -> None:
        @dataclass
        class EnumQuestions(Questions):
            priority: Annotated[Priority, Question(title="Priority")]

        result = EnumQuestions.validate_answers({"priority": 2})
        assert result["priority"] == Priority.MEDIUM


class TestOptionalAndDefaults:
    """Tests for optional fields and default values."""

    def test_optional_field_with_none(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 90, "rating": 4.5, "category": "C", "optional_field": None}
        )
        assert result["optional_field"] is None

    def test_optional_field_omitted(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 90, "rating": 4.5, "category": "C"}
        )
        assert result["optional_field"] is None

    def test_optional_field_with_value(self) -> None:
        result = ValidationQuestions.validate_answers(
            {
                "score": 90,
                "rating": 4.5,
                "category": "C",
                "optional_field": "some text",
            }
        )
        assert result["optional_field"] == "some text"

    def test_default_value_used_when_omitted(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 90, "rating": 4.5, "category": "C"}
        )
        assert result["with_default"] == 42

    def test_default_value_can_be_overridden(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 90, "rating": 4.5, "category": "C", "with_default": 99}
        )
        assert result["with_default"] == 99


class TestTypeCoercion:
    """Tests for automatic type coercion."""

    def test_coerce_string_to_int(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": "75", "rating": 3.5, "category": "A"}
        )
        assert result["score"] == 75
        assert isinstance(result["score"], int)

    def test_coerce_string_to_float(self) -> None:
        result = ValidationQuestions.validate_answers(
            {"score": 75, "rating": "4.2", "category": "A"}
        )
        assert result["rating"] == 4.2
        assert isinstance(result["rating"], float)

    def test_coerce_string_to_path(self) -> None:
        @dataclass
        class PathQuestions(Questions):
            location: Annotated[Path, Question(title="Path")]

        result = PathQuestions.validate_answers({"location": "/tmp/file.txt"})
        assert result["location"] == Path("/tmp/file.txt")
        assert isinstance(result["location"], Path)

    def test_coerce_bool_from_string(self) -> None:
        @dataclass
        class BoolQuestions(Questions):
            enabled: Annotated[bool, Question(title="Enabled")]

        result = BoolQuestions.validate_answers({"enabled": "true"})
        assert result["enabled"] is True

        result = BoolQuestions.validate_answers({"enabled": "false"})
        assert result["enabled"] is False

    def test_coerce_bool_from_int(self) -> None:
        @dataclass
        class BoolQuestions(Questions):
            enabled: Annotated[bool, Question(title="Enabled")]

        result = BoolQuestions.validate_answers({"enabled": 1})
        assert result["enabled"] is True

        result = BoolQuestions.validate_answers({"enabled": 0})
        assert result["enabled"] is False


class TestLiteralType:
    """Tests for Literal type support."""

    def test_literal_valid_value(self) -> None:
        @dataclass
        class LiteralQuestions(Questions):
            mode: Annotated[Literal["read", "write"], Question(title="Mode")]

        result = LiteralQuestions.validate_answers({"mode": "read"})
        assert result["mode"] == "read"

    def test_literal_invalid_value_raises(self) -> None:
        @dataclass
        class LiteralQuestions(Questions):
            mode: Annotated[Literal["read", "write"], Question(title="Mode")]

        with pytest.raises(ValueError, match="must be one of"):
            LiteralQuestions.validate_answers({"mode": "delete"})


class TestSerializationDeserialization:
    """Tests for custom serializer and deserializer."""

    def test_custom_serializer(self) -> None:
        @dataclass
        class CustomQuestions(Questions):
            value: Annotated[
                int,
                Question(
                    title="Value",
                    serializer=lambda x: f"${x}",
                    deserializer=lambda x: int(x.lstrip("$")),
                ),
            ]

        schema = CustomQuestions.ui_schema()
        assert schema[0]["title"] == "Value"

        definitions = CustomQuestions.definitions()
        question = definitions[0].question
        assert question.serialize(100) == "$100"
        assert question.deserialize("$100") == 100


class TestDoubleDefault:
    """Test that defining defaults in both Question and dataclass field raises error."""

    def test_double_default_raises(self) -> None:
        with pytest.raises(ValueError, match="default defined both"):

            @dataclass
            class BadQuestions(Questions):
                value: Annotated[int, Question(title="Value", default=10)] = 20


class TestInvalidFieldDefinitions:
    """Tests for invalid field definitions."""

    def test_missing_annotated_raises(self) -> None:
        with pytest.raises(TypeError, match="must use typing.Annotated"):

            @dataclass
            class BadQuestions(Questions):
                value: int  # type: ignore[misc]

            BadQuestions.definitions()

    def test_missing_question_metadata_raises(self) -> None:
        with pytest.raises(TypeError, match="missing Question metadata"):

            @dataclass
            class BadQuestions(Questions):
                value: Annotated[int, "some other metadata"]

            BadQuestions.definitions()
