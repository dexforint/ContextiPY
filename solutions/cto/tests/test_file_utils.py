from __future__ import annotations

import mimetypes
from pathlib import Path

import pytest

from contextipy import Audio, File, Image, Json, Text, Video
from contextipy.utils import (
    Extension,
    detect_file_type,
    get_mime_type,
    is_valid_file_type,
    sanitize_filename,
    safe_join,
    temp_directory,
    validate_file_types,
)


class TestExtension:
    """Tests for the Extension class and pattern matching."""

    def test_create_extension_single_pattern(self) -> None:
        ext = Extension(".jpg")
        assert ".jpg" in ext.patterns
        assert len(ext.patterns) == 1

    def test_create_extension_multiple_patterns(self) -> None:
        ext = Extension([".jpg", ".jpeg", ".png"])
        assert ext.patterns == (".jpg", ".jpeg", ".png")

    def test_create_extension_without_dot_prefix(self) -> None:
        ext = Extension("jpg")
        assert ".jpg" in ext.patterns

    def test_create_extension_normalizes_case(self) -> None:
        ext = Extension([".JPG", ".Jpeg"])
        assert ext.patterns == (".jpg", ".jpeg")

    def test_create_extension_empty_patterns_raises(self) -> None:
        with pytest.raises(ValueError, match="must contain at least one value"):
            Extension([])

    def test_create_extension_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            Extension("")

    def test_matches_existing_extension(self) -> None:
        ext = Extension([".jpg", ".png"])
        assert ext.matches(Path("photo.jpg"))
        assert ext.matches(Path("image.png"))

    def test_matches_uppercase_extension(self) -> None:
        ext = Extension(".png")
        assert ext.matches(Path("IMAGE.PNG"))

    def test_matches_path_string(self) -> None:
        ext = Extension(".txt")
        assert ext.matches("document.txt")

    def test_does_not_match_different_extension(self) -> None:
        ext = Extension([".jpg", ".png"])
        assert not ext.matches(Path("video.mp4"))

    def test_does_not_match_no_extension(self) -> None:
        ext = Extension(".txt")
        assert not ext.matches(Path("README"))


class TestFileTypeDetection:
    """Tests for file type detection using extensions and MIME."""

    def test_detect_image_by_png_extension(self) -> None:
        marker = detect_file_type(Path("photo.png"))
        assert marker == Image

    def test_detect_image_by_jpg_extension(self) -> None:
        marker = detect_file_type(Path("photo.jpg"))
        assert marker == Image

    def test_detect_video_by_mp4_extension(self) -> None:
        marker = detect_file_type(Path("movie.mp4"))
        assert marker == Video

    def test_detect_audio_by_mp3_extension(self) -> None:
        marker = detect_file_type(Path("song.mp3"))
        assert marker == Audio

    def test_detect_text_by_txt_extension(self) -> None:
        marker = detect_file_type(Path("document.txt"))
        assert marker == Text

    def test_detect_uppercase_extension(self) -> None:
        marker = detect_file_type(Path("PHOTO.PNG"))
        assert marker == Image

    def test_detect_file_without_extension(self) -> None:
        marker = detect_file_type(Path("README"))
        assert marker == File

    def test_detect_unknown_extension_fallback_to_file(self) -> None:
        marker = detect_file_type(Path("data.xyz"))
        assert marker == File

    def test_detect_with_mime_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_guess_type(_path: str) -> tuple[str, None]:
            return ("application/json", None)

        monkeypatch.setattr(mimetypes, "guess_type", fake_guess_type)
        marker = detect_file_type(Path("data.custom"))
        assert marker == Json

    def test_detect_from_string_path(self) -> None:
        marker = detect_file_type("document.txt")
        assert marker == Text


class TestGetMimeType:
    """Tests for MIME type detection."""

    def test_get_mime_for_png(self) -> None:
        mime = get_mime_type(Path("photo.png"))
        assert mime == "image/png"

    def test_get_mime_for_mp4(self) -> None:
        mime = get_mime_type(Path("video.mp4"))
        assert mime == "video/mp4"

    def test_get_mime_for_unknown_extension(self) -> None:
        mime = get_mime_type(Path("data.xyz"))
        assert mime is None

    def test_get_mime_from_string_path(self) -> None:
        mime = get_mime_type("song.mp3")
        assert mime is not None
        assert mime.startswith("audio/")


class TestIsValidFileType:
    """Tests for single file validation against type specifications."""

    def test_valid_with_marker(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), Image)

    def test_invalid_with_marker(self) -> None:
        assert not is_valid_file_type(Path("song.mp3"), Image)

    def test_valid_with_extension(self) -> None:
        ext = Extension([".jpg", ".png"])
        assert is_valid_file_type(Path("photo.jpg"), ext)

    def test_invalid_with_extension(self) -> None:
        ext = Extension([".jpg", ".png"])
        assert not is_valid_file_type(Path("video.mp4"), ext)

    def test_valid_with_string_spec(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), "image")

    def test_invalid_with_string_spec(self) -> None:
        assert not is_valid_file_type(Path("song.mp3"), "image")

    def test_valid_with_union_string_spec(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), "image | video")
        assert is_valid_file_type(Path("movie.mp4"), "image | video")

    def test_invalid_with_union_string_spec(self) -> None:
        assert not is_valid_file_type(Path("song.mp3"), "image | video")

    def test_valid_with_extension_string_spec(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), "extension(['.jpg', '.png'])")

    def test_invalid_with_extension_string_spec(self) -> None:
        assert not is_valid_file_type(Path("photo.gif"), "extension(['.jpg', '.png'])")

    def test_valid_with_mixed_union_spec(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), "image | extension(['.txt'])")
        assert is_valid_file_type(Path("note.txt"), "image | extension(['.txt'])")

    def test_valid_with_list_spec(self) -> None:
        assert is_valid_file_type(Path("photo.jpg"), [Image, Video])

    def test_uppercase_extension_matches(self) -> None:
        assert is_valid_file_type(Path("PHOTO.JPG"), Image)

    def test_empty_spec_raises(self) -> None:
        with pytest.raises(ValueError, match="Type specification string is empty"):
            is_valid_file_type(Path("file.txt"), "")

    def test_unknown_marker_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown type specification"):
            is_valid_file_type(Path("file.txt"), "unknown")


class TestValidateFileTypes:
    """Tests for multiple file validation."""

    def test_validate_single_file(self) -> None:
        result = validate_file_types([Path("photo.jpg")], Image)
        assert result == (Path("photo.jpg"),)

    def test_validate_multiple_files(self) -> None:
        files = [Path("photo1.jpg"), Path("photo2.png")]
        result = validate_file_types(files, Image)
        assert result == (Path("photo1.jpg"), Path("photo2.png"))

    def test_validate_empty_list(self) -> None:
        result = validate_file_types([], Image)
        assert result == tuple()

    def test_validate_with_union_spec(self) -> None:
        files = [Path("photo.jpg"), Path("video.mp4")]
        result = validate_file_types(files, "image | video")
        assert len(result) == 2

    def test_validate_with_extension_spec(self) -> None:
        files = [Path("data.csv"), Path("report.csv")]
        result = validate_file_types(files, Extension(".csv"))
        assert len(result) == 2

    def test_validate_string_paths(self) -> None:
        files = ["photo.jpg", "image.png"]
        result = validate_file_types(files, Image)
        assert result == (Path("photo.jpg"), Path("image.png"))

    def test_validate_mixed_uppercase_extensions(self) -> None:
        files = [Path("photo.jpg"), Path("IMAGE.PNG")]
        result = validate_file_types(files, Image)
        assert len(result) == 2

    def test_validate_fails_on_invalid_file(self) -> None:
        files = [Path("photo.jpg"), Path("song.mp3")]
        with pytest.raises(ValueError, match="does not satisfy required file types"):
            validate_file_types(files, Image)

    def test_validate_fails_with_descriptive_message(self) -> None:
        with pytest.raises(ValueError, match="song.mp3.*Image"):
            validate_file_types([Path("song.mp3")], Image)

    def test_validate_fails_with_union_description(self) -> None:
        with pytest.raises(ValueError, match="Image | Video"):
            validate_file_types([Path("song.mp3")], "image | video")


class TestParseExtensionSpec:
    """Tests for parsing extension specifications from strings."""

    def test_parse_extension_with_brackets(self) -> None:
        assert is_valid_file_type(Path("file.txt"), "extension(['.txt'])")

    def test_parse_extension_without_brackets(self) -> None:
        assert is_valid_file_type(Path("file.txt"), "extension('.txt')")

    def test_parse_extension_with_multiple_patterns(self) -> None:
        assert is_valid_file_type(Path("file.csv"), "extension(['.csv', '.tsv'])")

    def test_parse_extension_with_comma_separated(self) -> None:
        assert is_valid_file_type(Path("file.csv"), "extension('.csv', '.tsv')")

    def test_parse_extension_without_quotes(self) -> None:
        assert is_valid_file_type(Path("file.csv"), "extension([.csv, .tsv])")

    def test_parse_extension_without_quotes_or_brackets(self) -> None:
        assert is_valid_file_type(Path("file.csv"), "extension(.csv, .tsv)")

    def test_parse_extension_without_quotes_single_value(self) -> None:
        assert is_valid_file_type(Path("file.csv"), "extension(.csv)")

    def test_parse_extension_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must include at least one pattern"):
            is_valid_file_type(Path("file.txt"), "extension()")

    def test_parse_extension_with_invalid_syntax_raises(self) -> None:
        with pytest.raises(ValueError, match="must be valid Python literals"):
            is_valid_file_type(Path("file.txt"), "extension([invalid syntax here])")


class TestTempDirectory:
    """Tests for temporary directory utilities."""

    def test_temp_directory_created(self) -> None:
        with temp_directory() as temp_path:
            assert temp_path.exists()
            assert temp_path.is_dir()

    def test_temp_directory_cleaned_up(self) -> None:
        temp_path_copy = None
        with temp_directory() as temp_path:
            temp_path_copy = temp_path
            assert temp_path.exists()
        assert temp_path_copy is not None
        assert not temp_path_copy.exists()

    def test_temp_directory_with_prefix(self) -> None:
        with temp_directory(prefix="test_") as temp_path:
            assert temp_path.name.startswith("test_")

    def test_temp_directory_allows_file_creation(self) -> None:
        with temp_directory() as temp_path:
            test_file = temp_path / "test.txt"
            test_file.write_text("content")
            assert test_file.exists()
            assert test_file.read_text() == "content"


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_sanitize_simple_name(self) -> None:
        result = sanitize_filename("hello")
        assert result == "hello"

    def test_sanitize_name_with_extension(self) -> None:
        result = sanitize_filename("document.txt")
        assert result == "document.txt"

    def test_sanitize_removes_special_characters(self) -> None:
        result = sanitize_filename("hello@world#test")
        assert result == "hello_world_test"

    def test_sanitize_preserves_hyphens(self) -> None:
        result = sanitize_filename("file-name-test")
        assert result == "file-name-test"

    def test_sanitize_preserves_underscores(self) -> None:
        result = sanitize_filename("file_name_test")
        assert result == "file_name_test"

    def test_sanitize_preserves_dots(self) -> None:
        result = sanitize_filename("my.file.txt")
        assert result == "my.file.txt"

    def test_sanitize_removes_spaces(self) -> None:
        result = sanitize_filename("hello world")
        assert result == "hello_world"

    def test_sanitize_removes_slashes(self) -> None:
        result = sanitize_filename("path/to/file")
        assert result == "path_to_file"

    def test_sanitize_collapses_consecutive_replacements(self) -> None:
        result = sanitize_filename("hello@@world")
        assert result == "hello_world"

    def test_sanitize_handles_unicode(self) -> None:
        result = sanitize_filename("café")
        assert result == "cafe"

    def test_sanitize_strips_leading_trailing(self) -> None:
        result = sanitize_filename(" .file. ")
        assert result == "file"

    def test_sanitize_empty_becomes_file(self) -> None:
        result = sanitize_filename("")
        assert result == "file"

    def test_sanitize_special_only_becomes_file(self) -> None:
        result = sanitize_filename("@@@")
        assert result == "file"

    def test_sanitize_truncates_long_names(self) -> None:
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 255

    def test_sanitize_custom_replacement(self) -> None:
        result = sanitize_filename("hello world", replacement="-")
        assert result == "hello-world"

    def test_sanitize_empty_replacement_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            sanitize_filename("hello", replacement="")


class TestSafeJoin:
    """Tests for safe path joining."""

    def test_safe_join_simple_path(self) -> None:
        result = safe_join("/base", "sub", "file.txt")
        assert result == Path("/base/sub/file.txt")

    def test_safe_join_with_path_objects(self) -> None:
        result = safe_join(Path("/base"), Path("sub"), Path("file.txt"))
        assert result == Path("/base/sub/file.txt")

    def test_safe_join_normalizes_path(self) -> None:
        result = safe_join("/base", "sub/../sub2", "file.txt")
        assert result == Path("/base/sub2/file.txt")

    def test_safe_join_stays_within_base(self) -> None:
        result = safe_join("/base", "sub", "file.txt")
        assert str(result).startswith("/base")

    def test_safe_join_with_empty_parts(self) -> None:
        result = safe_join("/base", "", "file.txt")
        assert result == Path("/base/file.txt")

    def test_safe_join_raises_when_outside_base(self) -> None:
        with pytest.raises(ValueError, match="escapes the base directory"):
            safe_join("/base", "../etc/passwd")


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_detect_complex_path(self) -> None:
        marker = detect_file_type(Path("/path/to/nested/folder/image.jpg"))
        assert marker == Image

    def test_validate_with_invalid_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Type specifications must"):
            is_valid_file_type(Path("file.txt"), 123)  # type: ignore[arg-type]

    def test_validate_multiple_with_invalid_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Type specifications must"):
            validate_file_types([Path("file.txt")], 123)  # type: ignore[arg-type]

    def test_extension_from_single_string(self) -> None:
        ext = Extension(".txt")
        assert len(ext.patterns) == 1
        assert ".txt" in ext.patterns

    def test_complex_union_spec(self) -> None:
        spec = "image | video | audio"
        assert is_valid_file_type(Path("photo.jpg"), spec)
        assert is_valid_file_type(Path("video.mp4"), spec)
        assert is_valid_file_type(Path("song.mp3"), spec)
        assert not is_valid_file_type(Path("doc.txt"), spec)

    def test_no_extension_files(self) -> None:
        marker = detect_file_type(Path("Makefile"))
        assert marker == File

    def test_hidden_files(self) -> None:
        marker = detect_file_type(Path(".gitignore"))
        assert marker == File

    def test_multiple_dots_in_filename(self) -> None:
        marker = detect_file_type(Path("my.test.file.png"))
        assert marker == Image
