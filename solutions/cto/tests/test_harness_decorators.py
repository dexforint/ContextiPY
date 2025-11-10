"""Tests covering decorator registration flows using shared fixtures."""

from __future__ import annotations

import pytest

from contextipy import (
    RegistrationError,
    get_metadata,
    oneshot_script,
    service,
    service_script,
)
from contextipy.core import OneshotScriptMetadata, ServiceMetadata, ServiceScriptMetadata


@pytest.mark.usefixtures("isolated_registry")
class TestDecoratorRegistration:
    """Tests ensuring decorators populate metadata correctly."""

    def test_oneshot_script_metadata(self) -> None:
        """Verify oneshot_script decorator attaches metadata."""

        @oneshot_script(
            script_id="sample",
            title="Sample Script",
            description="Simple script",
            timeout=2.5,
        )
        def sample(name: str) -> str:
            return name.title()

        metadata = get_metadata(sample)
        assert metadata is not None
        assert isinstance(metadata, OneshotScriptMetadata)
        assert metadata.id == "sample"
        assert metadata.title == "Sample Script"
        assert metadata.description == "Simple script"
        assert metadata.timeout == 2.5
        assert metadata.parameters[0].name == "name"

    def test_service_metadata(self) -> None:
        """Verify service decorator attaches metadata."""

        @service(
            service_id="svc",
            title="Sample Service",
            description="Service under test",
        )
        def svc() -> None:
            return None

        metadata = get_metadata(svc)
        assert metadata is not None
        assert isinstance(metadata, ServiceMetadata)
        assert metadata.id == "svc"
        assert metadata.title == "Sample Service"
        assert metadata.description == "Service under test"

    def test_service_script_metadata(self) -> None:
        """Verify service_script decorator attaches metadata and links service."""

        @service(
            service_id="svc",
            title="Sample Service",
            description="Service under test",
        )
        def svc() -> None:
            return None

        @service_script(
            script_id="svc-start",
            service_id="svc",
            title="Start",
            description="Start the service",
        )
        def start() -> None:
            return None

        svc_metadata = get_metadata(svc)
        script_metadata = get_metadata(start)

        assert svc_metadata is not None
        assert script_metadata is not None
        assert isinstance(svc_metadata, ServiceMetadata)
        assert isinstance(script_metadata, ServiceScriptMetadata)
        assert svc_metadata.service_scripts[0].id == "svc-start"
        assert script_metadata.service_id == "svc"

    def test_duplicate_registration_raises(self) -> None:
        """Ensure duplicate script IDs raise a registration error."""

        @oneshot_script(
            script_id="duplicate",
            title="Duplicate",
            description="First",
        )
        def first() -> None:
            return None

        with pytest.raises(RegistrationError):

            @oneshot_script(
                script_id="duplicate",
                title="Duplicate",
                description="Second",
            )
            def second() -> None:
                return None

        # Ensure first metadata still exists
        metadata = get_metadata(first)
        assert metadata is not None
        assert metadata.id == "duplicate"
