"""Unit tests for question types and metadata."""

from pathlib import Path

import pytest

from contextipy.questions import ImageQuery, Question
from contextipy.questions.types import UNSET


class TestQuestion:
    """Tests for the Question base class."""

    def test_create_basic_question(self) -> None:
        q = Question(title="Name")
        assert q.title == "Name"
        assert q.description is None
        assert q.default is UNSET
        assert q.required is True
        assert q.enum is None
        assert q.ge is None
        assert q.le is None
        assert q.kind == "text"

    def test_create_question_with_description(self) -> None:
        q = Question(title="Age", description="Your age in years")
        assert q.title == "Age"
        assert q.description == "Your age in years"

    def test_create_question_with_default(self) -> None:
        q = Question(title="Name", default="Alice")
        assert q.default == "Alice"
        assert q.has_default is True

    def test_question_without_default(self) -> None:
        q = Question(title="Name")
        assert q.has_default is False

    def test_create_optional_question(self) -> None:
        q = Question(title="Email", required=False)
        assert q.required is False

    def test_create_question_with_enum(self) -> None:
        q = Question(title="Color", enum=["red", "green", "blue"])
        assert q.enum == ("red", "green", "blue")

    def test_question_enum_converted_to_tuple(self) -> None:
        q = Question(title="Size", enum=["S", "M", "L"])
        assert isinstance(q.enum, tuple)
        assert q.enum == ("S", "M", "L")

    def test_question_empty_enum_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            Question(title="Empty", enum=[])

    def test_question_duplicate_enum_values_raises(self) -> None:
        with pytest.raises(ValueError, match="must be unique"):
            Question(title="Duplicates", enum=["a", "b", "a"])

    def test_create_question_with_ge(self) -> None:
        q = Question(title="Score", ge=0.0)
        assert q.ge == 0.0

    def test_create_question_with_le(self) -> None:
        q = Question(title="Score", le=100.0)
        assert q.le == 100.0

    def test_create_question_with_both_ge_and_le(self) -> None:
        q = Question(title="Score", ge=0.0, le=100.0)
        assert q.ge == 0.0
        assert q.le == 100.0

    def test_question_ge_greater_than_le_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be greater than"):
            Question(title="Invalid", ge=100.0, le=50.0)

    def test_question_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty title"):
            Question(title="")

    def test_question_serialize_value(self) -> None:
        q = Question[int](title="Count")
        assert q.serialize(42) == 42
        assert q.serialize(None) is None

    def test_question_serialize_with_custom_serializer(self) -> None:
        q = Question[int](title="Count", serializer=lambda x: str(x))
        assert q.serialize(42) == "42"
        assert q.serialize(None) is None

    def test_question_deserialize_value(self) -> None:
        q = Question[int](title="Count")
        assert q.deserialize(42) == 42
        assert q.deserialize(None) is None

    def test_question_deserialize_with_custom_deserializer(self) -> None:
        q = Question[int](title="Count", deserializer=lambda x: int(x))
        assert q.deserialize("42") == 42
        assert q.deserialize(None) is None


class TestImageQuery:
    """Tests for the ImageQuery specialized question."""

    def test_create_image_query(self) -> None:
        q = ImageQuery(title="Select profile picture")
        assert q.title == "Select profile picture"
        assert q.kind == "image"
        assert q.formats == ("png", "jpg", "jpeg", "gif", "bmp", "webp")

    def test_create_image_query_with_description(self) -> None:
        q = ImageQuery(title="Logo", description="Select your company logo")
        assert q.description == "Select your company logo"

    def test_create_image_query_with_custom_formats(self) -> None:
        q = ImageQuery(title="Photo", formats=["png", "jpg"])
        assert q.formats == ("png", "jpg")

    def test_create_image_query_optional(self) -> None:
        q = ImageQuery(title="Avatar", required=False)
        assert q.required is False

    def test_create_image_query_with_default_path(self) -> None:
        default_path = Path("/tmp/default.png")
        q = ImageQuery(title="Image", default=default_path)
        assert q.default == default_path

    def test_create_image_query_with_default_string(self) -> None:
        q = ImageQuery(title="Image", default="/tmp/default.png")
        assert q.default == Path("/tmp/default.png")

    def test_image_query_serialize_path(self) -> None:
        q = ImageQuery(title="Photo")
        path = Path("/tmp/photo.jpg")
        assert q.serialize(path) == "/tmp/photo.jpg"

    def test_image_query_serialize_none(self) -> None:
        q = ImageQuery(title="Photo")
        assert q.serialize(None) is None

    def test_image_query_deserialize_path(self) -> None:
        q = ImageQuery(title="Photo")
        path = Path("/tmp/photo.jpg")
        assert q.deserialize(path) == path

    def test_image_query_deserialize_string(self) -> None:
        q = ImageQuery(title="Photo")
        result = q.deserialize("/tmp/photo.jpg")
        assert result == Path("/tmp/photo.jpg")

    def test_image_query_deserialize_none(self) -> None:
        q = ImageQuery(title="Photo")
        assert q.deserialize(None) is None

    def test_image_query_deserialize_invalid_type_raises(self) -> None:
        q = ImageQuery(title="Photo")
        with pytest.raises(TypeError, match="path strings"):
            q.deserialize(123)
