"""Unit tests for the core decorator functionality."""

from pathlib import Path
from typing import Any

import pytest

from contextipy import (
    Audio,
    File,
    Image,
    Param,
    RegistrationError,
    get_metadata,
    oneshot_script,
    service,
    service_script,
)
from contextipy.core import OneshotScriptMetadata, ServiceMetadata, ServiceScriptMetadata


class TestOneshotScriptDecorator:
    """Tests for the @oneshot_script decorator."""

    def test_basic_oneshot_script(self) -> None:
        @oneshot_script(
            script_id="test_script",
            title="Test Script",
            description="A test script",
        )
        def my_script(arg: str) -> str:
            return arg.upper()

        metadata = get_metadata(my_script)
        assert metadata is not None
        assert isinstance(metadata, OneshotScriptMetadata)
        assert metadata.id == "test_script"
        assert metadata.title == "Test Script"
        assert metadata.description == "A test script"
        assert metadata.timeout is None
        assert metadata.accepts == ()
        assert metadata.parameters == ()
        assert metadata.target is my_script

    def test_oneshot_script_with_inputs(self) -> None:
        @oneshot_script(
            script_id="image_processor",
            title="Image Processor",
            description="Processes images",
            accepts=[Image, File],
        )
        def process_image(path: Path) -> Path:
            return path

        metadata = get_metadata(process_image)
        assert metadata is not None
        assert len(metadata.accepts) == 2
        assert metadata.accepts[0] == Image
        assert metadata.accepts[1] == File

    def test_oneshot_script_with_params(self) -> None:
        @oneshot_script(
            script_id="resize_image",
            title="Resize Image",
            description="Resize an image",
            params=[
                Param("width", "Width", "Target width"),
                Param("height", "Height", "Target height"),
            ],
        )
        def resize(path: Path, width: int = 100, height: int = 100) -> Path:
            return path

        metadata = get_metadata(resize)
        assert metadata is not None
        assert len(metadata.parameters) == 2

        width_param = metadata.parameters[0]
        assert width_param.name == "width"
        assert width_param.title == "Width"
        assert width_param.description == "Target width"
        assert width_param.annotation == int
        assert not width_param.required
        assert width_param.default == 100

        height_param = metadata.parameters[1]
        assert height_param.name == "height"
        assert height_param.title == "Height"
        assert height_param.description == "Target height"
        assert height_param.annotation == int
        assert not height_param.required
        assert height_param.default == 100

    def test_oneshot_script_with_timeout(self) -> None:
        @oneshot_script(
            script_id="slow_script",
            title="Slow Script",
            description="A slow script",
            timeout=30.0,
        )
        def slow() -> None:
            pass

        metadata = get_metadata(slow)
        assert metadata is not None
        assert metadata.timeout == 30.0

    def test_oneshot_script_missing_id(self) -> None:
        with pytest.raises(RegistrationError, match="script_id must be provided"):

            @oneshot_script(
                script_id="",
                title="Test",
                description="Test",
            )
            def bad() -> None:
                pass

    def test_oneshot_script_missing_title(self) -> None:
        with pytest.raises(RegistrationError, match="title must be provided"):

            @oneshot_script(
                script_id="test",
                title="",
                description="Test",
            )
            def bad() -> None:
                pass

    def test_oneshot_script_missing_description(self) -> None:
        with pytest.raises(RegistrationError, match="description must be provided"):

            @oneshot_script(
                script_id="test",
                title="Test",
                description="",
            )
            def bad() -> None:
                pass

    def test_oneshot_script_missing_type_annotation(self) -> None:
        with pytest.raises(RegistrationError, match="must have a type annotation"):

            @oneshot_script(
                script_id="bad_script",
                title="Bad Script",
                description="Missing type annotation",
            )
            def bad(arg):  # type: ignore
                return arg

    def test_oneshot_script_missing_return_annotation(self) -> None:
        with pytest.raises(RegistrationError, match="must declare a return type annotation"):

            @oneshot_script(
                script_id="bad_return",
                title="Bad Return",
                description="Missing return annotation",
            )
            def bad(arg: str):  # type: ignore
                return arg

    def test_oneshot_script_duplicate_id(self) -> None:
        @oneshot_script(
            script_id="duplicate",
            title="First",
            description="First script",
        )
        def first() -> None:
            pass

        with pytest.raises(RegistrationError, match="already registered"):

            @oneshot_script(
                script_id="duplicate",
                title="Second",
                description="Second script",
            )
            def second() -> None:
                pass


class TestServiceDecorator:
    """Tests for the @service decorator."""

    def test_basic_service(self) -> None:
        @service(
            service_id="test_service",
            title="Test Service",
            description="A test service",
        )
        def my_service() -> None:
            pass

        metadata = get_metadata(my_service)
        assert metadata is not None
        assert isinstance(metadata, ServiceMetadata)
        assert metadata.id == "test_service"
        assert metadata.title == "Test Service"
        assert metadata.description == "A test service"
        assert metadata.timeout is None
        assert metadata.accepts == ()
        assert metadata.parameters == ()
        assert metadata.service_scripts == ()
        assert metadata.target is my_service

    def test_service_with_timeout(self) -> None:
        @service(
            service_id="slow_service",
            title="Slow Service",
            description="A slow service",
            timeout=60.0,
        )
        def slow() -> None:
            pass

        metadata = get_metadata(slow)
        assert metadata is not None
        assert metadata.timeout == 60.0

    def test_service_missing_id(self) -> None:
        with pytest.raises(RegistrationError, match="service_id must be provided"):

            @service(
                service_id="",
                title="Test",
                description="Test",
            )
            def bad() -> None:
                pass

    def test_service_missing_title(self) -> None:
        with pytest.raises(RegistrationError, match="title must be provided"):

            @service(
                service_id="test",
                title="",
                description="Test",
            )
            def bad() -> None:
                pass

    def test_service_missing_description(self) -> None:
        with pytest.raises(RegistrationError, match="description must be provided"):

            @service(
                service_id="test",
                title="Test",
                description="",
            )
            def bad() -> None:
                pass


class TestServiceScriptDecorator:
    """Tests for the @service_script decorator."""

    def test_basic_service_script(self) -> None:
        @service(
            service_id="my_service",
            title="My Service",
            description="A service",
        )
        def my_service() -> None:
            pass

        @service_script(
            script_id="my_script",
            service_id="my_service",
            title="My Script",
            description="A service script",
        )
        def my_script() -> None:
            pass

        script_metadata = get_metadata(my_script)
        assert script_metadata is not None
        assert isinstance(script_metadata, ServiceScriptMetadata)
        assert script_metadata.id == "my_script"
        assert script_metadata.service_id == "my_service"
        assert script_metadata.title == "My Script"
        assert script_metadata.description == "A service script"
        assert script_metadata.target is my_script

        service_metadata = get_metadata(my_service)
        assert service_metadata is not None
        assert isinstance(service_metadata, ServiceMetadata)
        assert len(service_metadata.service_scripts) == 1
        assert service_metadata.service_scripts[0] is script_metadata

    def test_service_script_with_params(self) -> None:
        @service(
            service_id="config_service",
            title="Config Service",
            description="Configuration service",
        )
        def config_service() -> None:
            pass

        @service_script(
            script_id="set_config",
            service_id="config_service",
            title="Set Config",
            description="Set a configuration value",
            params=[
                Param("key", "Key", "Configuration key"),
                Param("value", "Value", "Configuration value"),
            ],
        )
        def set_config(key: str, value: str) -> None:
            pass

        metadata = get_metadata(set_config)
        assert metadata is not None
        assert len(metadata.parameters) == 2

    def test_service_script_missing_service(self) -> None:
        with pytest.raises(RegistrationError, match="Service .* has not been registered"):

            @service_script(
                script_id="orphan_script",
                service_id="nonexistent_service",
                title="Orphan Script",
                description="Script without service",
            )
            def orphan() -> None:
                pass

    def test_multiple_service_scripts(self) -> None:
        @service(
            service_id="multi_service",
            title="Multi Service",
            description="A service with multiple scripts",
        )
        def multi_service() -> None:
            pass

        @service_script(
            script_id="script_1",
            service_id="multi_service",
            title="Script 1",
            description="First script",
        )
        def script_1() -> None:
            pass

        @service_script(
            script_id="script_2",
            service_id="multi_service",
            title="Script 2",
            description="Second script",
        )
        def script_2() -> None:
            pass

        service_metadata = get_metadata(multi_service)
        assert service_metadata is not None
        assert len(service_metadata.service_scripts) == 2
        assert service_metadata.service_scripts[0].id == "script_1"
        assert service_metadata.service_scripts[1].id == "script_2"


class TestParameterResolution:
    """Tests for parameter metadata resolution."""

    def test_required_parameter(self) -> None:
        @oneshot_script(
            script_id="required_param",
            title="Required Param",
            description="Script with required parameter",
            params=[Param("name", "Name", "User name")],
        )
        def script(name: str) -> str:
            return name

        metadata = get_metadata(script)
        assert metadata is not None
        assert len(metadata.parameters) == 1
        param = metadata.parameters[0]
        assert param.required
        assert param.annotation == str

    def test_optional_parameter(self) -> None:
        @oneshot_script(
            script_id="optional_param",
            title="Optional Param",
            description="Script with optional parameter",
            params=[Param("count", "Count", "Number of items")],
        )
        def script(count: int = 10) -> int:
            return count

        metadata = get_metadata(script)
        assert metadata is not None
        assert len(metadata.parameters) == 1
        param = metadata.parameters[0]
        assert not param.required
        assert param.default == 10

    def test_unknown_param_spec(self) -> None:
        with pytest.raises(
            RegistrationError,
            match="Param definitions provided for unknown parameters",
        ):

            @oneshot_script(
                script_id="unknown_param",
                title="Unknown Param",
                description="Script with unknown param spec",
                params=[Param("nonexistent", "Non-existent", "Does not exist")],
            )
            def script(actual: str) -> str:
                return actual

    def test_duplicate_param_spec(self) -> None:
        with pytest.raises(RegistrationError, match="Duplicate Param definition"):

            @oneshot_script(
                script_id="duplicate_param",
                title="Duplicate Param",
                description="Script with duplicate param spec",
                params=[
                    Param("value", "Value", "First definition"),
                    Param("value", "Value", "Second definition"),
                ],
            )
            def script(value: str) -> str:
                return value


class TestGetMetadata:
    """Tests for get_metadata utility."""

    def test_get_metadata_from_script(self) -> None:
        @oneshot_script(
            script_id="test",
            title="Test",
            description="Test",
        )
        def script() -> None:
            pass

        metadata = get_metadata(script)
        assert metadata is not None
        assert metadata.id == "test"

    def test_get_metadata_from_undecorated(self) -> None:
        def regular_function() -> None:
            pass

        metadata = get_metadata(regular_function)
        assert metadata is None


class TestInputMarkers:
    """Tests for InputMarker validation."""

    def test_valid_input_markers(self) -> None:
        @oneshot_script(
            script_id="multi_input",
            title="Multi Input",
            description="Script accepting multiple input types",
            accepts=[Image, Audio, File],
        )
        def script(path: Path) -> Path:
            return path

        metadata = get_metadata(script)
        assert metadata is not None
        assert len(metadata.accepts) == 3

    def test_invalid_input_marker(self) -> None:
        with pytest.raises(RegistrationError, match="is not an InputMarker"):

            @oneshot_script(
                script_id="bad_input",
                title="Bad Input",
                description="Script with invalid input marker",
                accepts=["not_a_marker"],  # type: ignore
            )
            def script(arg: str) -> str:
                return arg
