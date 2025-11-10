"""Unit tests for parameter specification utilities."""

import pytest

from contextipy import Param


class TestParam:
    """Tests for the Param dataclass."""

    def test_param_creation(self) -> None:
        param = Param("timeout", "Timeout", "Execution timeout in seconds")
        assert param.name == "timeout"
        assert param.title == "Timeout"
        assert param.description == "Execution timeout in seconds"
        assert param.annotation is None
        assert param.required is None

    def test_param_with_defaults(self) -> None:
        param = Param("retries", "Retries", "Number of retries", default=3, required=False)
        assert param.default == 3
        assert param.required is False

    def test_param_requires_name(self) -> None:
        with pytest.raises(ValueError, match="non-empty name"):
            Param("", "Title", "Desc")

    def test_param_requires_title(self) -> None:
        with pytest.raises(ValueError, match="non-empty title"):
            Param("name", "", "Desc")

    def test_param_requires_description(self) -> None:
        with pytest.raises(ValueError, match="non-empty description"):
            Param("name", "Title", "")
