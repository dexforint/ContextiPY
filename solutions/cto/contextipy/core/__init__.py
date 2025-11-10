"""Core API layer for Contextipy service and script registration."""

from .decorators import (
    RegistrationError,
    get_metadata,
    oneshot_script,
    service,
    service_script,
)
from .metadata import (
    BaseMetadata,
    OneshotScriptMetadata,
    ParameterMetadata,
    ServiceMetadata,
    ServiceScriptMetadata,
)
from .params import NO_DEFAULT, Param
from .types import Audio, File, Folder, Image, InputMarker, Json, Text, Url, Video

__all__ = [
    "oneshot_script",
    "service",
    "service_script",
    "get_metadata",
    "RegistrationError",
    "Param",
    "NO_DEFAULT",
    "InputMarker",
    "File",
    "Folder",
    "Image",
    "Text",
    "Url",
    "Audio",
    "Video",
    "Json",
    "BaseMetadata",
    "OneshotScriptMetadata",
    "ServiceMetadata",
    "ServiceScriptMetadata",
    "ParameterMetadata",
]
