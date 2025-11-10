"""Unit tests for metadata dataclasses."""

import pytest

from contextipy.core.metadata import (
    OneshotScriptMetadata,
    ParameterMetadata,
    ServiceMetadata,
    ServiceScriptMetadata,
)
from contextipy.core.types import File, Image


class TestParameterMetadata:
    """Tests for ParameterMetadata dataclass."""

    def test_parameter_metadata_creation(self) -> None:
        param = ParameterMetadata(
            name="width",
            title="Width",
            description="Image width",
            annotation=int,
            required=False,
            default=800,
        )
        assert param.name == "width"
        assert param.title == "Width"
        assert param.description == "Image width"
        assert param.annotation == int
        assert not param.required
        assert param.default == 800


class TestOneshotScriptMetadata:
    """Tests for OneshotScriptMetadata dataclass."""

    def test_basic_metadata(self) -> None:
        def dummy_func() -> None:
            pass

        metadata = OneshotScriptMetadata(
            id="test",
            title="Test Script",
            description="A test",
            timeout=None,
            accepts=(),
            parameters=(),
            target=dummy_func,
        )
        assert metadata.id == "test"
        assert metadata.title == "Test Script"
        assert metadata.description == "A test"
        assert metadata.kind == "oneshot"

    def test_metadata_with_inputs(self) -> None:
        def dummy_func() -> None:
            pass

        metadata = OneshotScriptMetadata(
            id="test",
            title="Test",
            description="Test",
            timeout=None,
            accepts=(Image, File),
            parameters=(),
            target=dummy_func,
        )
        assert len(metadata.accepts) == 2

    def test_metadata_is_frozen(self) -> None:
        def dummy_func() -> None:
            pass

        metadata = OneshotScriptMetadata(
            id="test",
            title="Test",
            description="Test",
            timeout=None,
            accepts=(),
            parameters=(),
            target=dummy_func,
        )
        with pytest.raises(Exception):
            metadata.id = "modified"  # type: ignore


class TestServiceMetadata:
    """Tests for ServiceMetadata dataclass."""

    def test_service_metadata(self) -> None:
        def dummy_func() -> None:
            pass

        metadata = ServiceMetadata(
            id="service",
            title="Test Service",
            description="A test service",
            timeout=None,
            accepts=(),
            parameters=(),
            target=dummy_func,
            service_scripts=(),
        )
        assert metadata.id == "service"
        assert metadata.title == "Test Service"
        assert metadata.kind == "service"
        assert len(metadata.service_scripts) == 0


class TestServiceScriptMetadata:
    """Tests for ServiceScriptMetadata dataclass."""

    def test_service_script_metadata(self) -> None:
        def dummy_func() -> None:
            pass

        metadata = ServiceScriptMetadata(
            id="script",
            service_id="service",
            title="Test Script",
            description="A test script",
            timeout=None,
            accepts=(),
            parameters=(),
            target=dummy_func,
        )
        assert metadata.id == "script"
        assert metadata.service_id == "service"
        assert metadata.title == "Test Script"
        assert metadata.kind == "service_script"
