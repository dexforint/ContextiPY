"""Unit tests for core type markers."""

from pathlib import Path

import pytest

from contextipy import Audio, File, Folder, Image, InputMarker, Json, Text, Url, Video


class TestInputMarker:
    """Tests for InputMarker creation and validation."""

    def test_create_marker(self) -> None:
        marker = InputMarker("custom", str, "A custom marker")
        assert marker.name == "custom"
        assert marker.python_type == str
        assert marker.description == "A custom marker"

    def test_create_marker_without_description(self) -> None:
        marker = InputMarker("simple", int)
        assert marker.name == "simple"
        assert marker.python_type == int
        assert marker.description is None

    def test_marker_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="must define a non-empty name"):
            InputMarker("", str)

    def test_marker_frozen(self) -> None:
        marker = InputMarker("frozen", str)
        with pytest.raises(Exception):
            marker.name = "modified"  # type: ignore

    def test_marker_repr(self) -> None:
        marker = InputMarker("test", str)
        repr_str = repr(marker)
        assert "test" in repr_str
        assert "str" in repr_str


class TestPredefinedMarkers:
    """Tests for predefined input markers."""

    def test_file_marker(self) -> None:
        assert File.name == "file"
        assert File.python_type == Path

    def test_folder_marker(self) -> None:
        assert Folder.name == "folder"
        assert Folder.python_type == Path

    def test_image_marker(self) -> None:
        assert Image.name == "image"
        assert Image.python_type == Path

    def test_text_marker(self) -> None:
        assert Text.name == "text"
        assert Text.python_type == str

    def test_url_marker(self) -> None:
        assert Url.name == "url"
        assert Url.python_type == str

    def test_audio_marker(self) -> None:
        assert Audio.name == "audio"
        assert Audio.python_type == Path

    def test_video_marker(self) -> None:
        assert Video.name == "video"
        assert Video.python_type == Path

    def test_json_marker(self) -> None:
        assert Json.name == "json"
        assert Json.python_type == str

    def test_markers_are_distinct(self) -> None:
        markers = {File, Folder, Image, Text, Url, Audio, Video, Json}
        assert len(markers) == 8
