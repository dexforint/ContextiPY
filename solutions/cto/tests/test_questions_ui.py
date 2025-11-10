"""Headless tests for the questions UI helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from contextipy.questions.ui import WidgetKind, ask, determine_widget_kind, validate_value


@pytest.fixture
def sample_text_question() -> dict[str, Any]:
    return {
        "name": "name",
        "title": "Full name",
        "kind": "text",
        "required": True,
    }


@pytest.fixture
def sample_int_question() -> dict[str, Any]:
    return {
        "name": "age",
        "title": "Age",
        "ge": 18,
        "le": 120,
        "required": True,
    }


@pytest.fixture
def sample_float_question() -> dict[str, Any]:
    return {
        "name": "weight",
        "title": "Weight",
        "ge": 0.0,
        "le": 200.5,
        "required": True,
    }


@pytest.fixture
def sample_enum_question() -> dict[str, Any]:
    return {
        "name": "colour",
        "title": "Favourite colour",
        "enum": ["Colour.RED", "Colour.GREEN", "Colour.BLUE"],
        "required": True,
    }


@pytest.fixture
def sample_image_question() -> dict[str, Any]:
    return {
        "name": "avatar",
        "title": "Profile picture",
        "kind": "image",
        "formats": ["png", "jpg"],
        "required": False,
    }


class TestDetermineWidgetKind:
    """Tests for widget type resolution."""

    def test_text_question(self, sample_text_question: dict[str, Any]) -> None:
        assert determine_widget_kind(sample_text_question) is WidgetKind.TEXT

    def test_integer_question_with_bounds(self, sample_int_question: dict[str, Any]) -> None:
        assert determine_widget_kind(sample_int_question) is WidgetKind.INTEGER

    def test_float_question_with_bounds(self, sample_float_question: dict[str, Any]) -> None:
        assert determine_widget_kind(sample_float_question) is WidgetKind.FLOAT

    def test_enum_question(self, sample_enum_question: dict[str, Any]) -> None:
        assert determine_widget_kind(sample_enum_question) is WidgetKind.ENUM

    def test_image_question(self, sample_image_question: dict[str, Any]) -> None:
        assert determine_widget_kind(sample_image_question) is WidgetKind.IMAGE

    def test_numeric_kind_hint(self) -> None:
        question = {
            "name": "count",
            "title": "Count",
            "kind": "integer",
            "required": True,
        }
        assert determine_widget_kind(question) is WidgetKind.INTEGER


class TestValidateValue:
    """Tests for value validation helper."""

    def test_required_text_field(self, sample_text_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_text_question, None)
        assert valid is False
        assert error == "This field is required"

    def test_optional_text_field(self, sample_text_question: dict[str, Any]) -> None:
        sample_text_question["required"] = False
        valid, error = validate_value(sample_text_question, None)
        assert valid is True
        assert error is None

    def test_integer_within_bounds(self, sample_int_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_int_question, 25)
        assert valid is True
        assert error is None

    def test_integer_below_lower_bound(self, sample_int_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_int_question, 10)
        assert valid is False
        assert error == "Value must be >= 18"

    def test_float_above_upper_bound(self, sample_float_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_float_question, 250.0)
        assert valid is False
        assert error == "Value must be <= 200.5"

    def test_float_with_string_input(self, sample_float_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_float_question, "not-a-number")
        assert valid is False
        assert error == "Value must be a number"

    def test_enum_valid_value(self, sample_enum_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_enum_question, "Colour.GREEN")
        assert valid is True
        assert error is None

    def test_enum_invalid_value(self, sample_enum_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_enum_question, "PURPLE")
        assert valid is False
        assert error == "Value must be one of: Colour.RED, Colour.GREEN, Colour.BLUE"

    def test_image_optional_blank(self, sample_image_question: dict[str, Any]) -> None:
        valid, error = validate_value(sample_image_question, None)
        assert valid is True
        assert error is None


class TestAskGuards:
    """Tests covering guard clauses in the ask() helper."""

    def test_ask_requires_pyside(self) -> None:
        schema = [{"name": "field", "title": "Field", "kind": "text"}]
        with patch("contextipy.questions.ui.PYSIDE_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="PySide6 is not available"):
                ask(schema)

    def test_ask_requires_qapplication(self) -> None:
        schema = [{"name": "field", "title": "Field", "kind": "text"}]

        class StubApp:
            @staticmethod
            def instance() -> None:
                return None

        with patch("contextipy.questions.ui.PYSIDE_AVAILABLE", True), patch(
            "contextipy.questions.ui.QApplication", StubApp
        ):
            with pytest.raises(RuntimeError, match="QApplication must be initialized"):
                ask(schema)
