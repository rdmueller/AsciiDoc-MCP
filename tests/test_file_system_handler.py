"""Tests for File System Handler.

Tests the atomic read/write operations as specified in ADR-004.
"""

import os
from pathlib import Path

import pytest

from dacli.file_handler import (
    FileReadError,
    FileSystemHandler,
    FileWriteError,
)


@pytest.fixture
def handler() -> FileSystemHandler:
    """Create a FileSystemHandler instance."""
    return FileSystemHandler()


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary test file."""
    file_path = tmp_path / "test.adoc"
    file_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n", encoding="utf-8")
    return file_path


@pytest.fixture
def temp_file_no_newline(tmp_path: Path) -> Path:
    """Create a temporary test file without trailing newline."""
    file_path = tmp_path / "test_no_newline.adoc"
    file_path.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")
    return file_path


# =============================================================================
# read_file() Tests
# =============================================================================


class TestReadFile:
    """Tests for read_file() method."""

    def test_read_file_success(self, handler: FileSystemHandler, temp_file: Path):
        """Successfully read a file."""
        content = handler.read_file(temp_file)
        assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"

    def test_read_file_utf8(self, handler: FileSystemHandler, tmp_path: Path):
        """Read file with UTF-8 characters."""
        file_path = tmp_path / "utf8.adoc"
        file_path.write_text("Ümläuts: äöü ß\nEmoji: 🎉\n", encoding="utf-8")

        content = handler.read_file(file_path)
        assert "Ümläuts: äöü ß" in content
        assert "🎉" in content

    def test_read_file_not_found(self, handler: FileSystemHandler, tmp_path: Path):
        """FileReadError for non-existent file."""
        with pytest.raises(FileReadError) as exc_info:
            handler.read_file(tmp_path / "nonexistent.adoc")

        assert "not found" in str(exc_info.value).lower()

    def test_read_file_permission_denied(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """FileReadError for permission denied."""
        # Make file unreadable
        os.chmod(temp_file, 0o000)
        try:
            with pytest.raises(FileReadError) as exc_info:
                handler.read_file(temp_file)
            assert "permission" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_file, 0o644)

    def test_read_file_encoding_error(
        self, handler: FileSystemHandler, tmp_path: Path
    ):
        """FileReadError for invalid UTF-8."""
        file_path = tmp_path / "invalid.adoc"
        # Write invalid UTF-8 bytes
        file_path.write_bytes(b"\x80\x81\x82 invalid utf-8")

        with pytest.raises(FileReadError) as exc_info:
            handler.read_file(file_path)
        assert "encoding" in str(exc_info.value).lower()

    def test_read_file_empty(self, handler: FileSystemHandler, tmp_path: Path):
        """Read empty file returns empty string."""
        file_path = tmp_path / "empty.adoc"
        file_path.write_text("", encoding="utf-8")

        content = handler.read_file(file_path)
        assert content == ""


# =============================================================================
# read_lines() Tests
# =============================================================================


class TestReadLines:
    """Tests for read_lines() method."""

    def test_read_lines_success(self, handler: FileSystemHandler, temp_file: Path):
        """Read specific line range."""
        lines = handler.read_lines(temp_file, start=2, end=4)
        assert lines == ["Line 2\n", "Line 3\n", "Line 4\n"]

    def test_read_lines_single_line(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Read single line."""
        lines = handler.read_lines(temp_file, start=3, end=3)
        assert lines == ["Line 3\n"]

    def test_read_lines_first_line(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Read first line."""
        lines = handler.read_lines(temp_file, start=1, end=1)
        assert lines == ["Line 1\n"]

    def test_read_lines_last_line(self, handler: FileSystemHandler, temp_file: Path):
        """Read last line."""
        lines = handler.read_lines(temp_file, start=5, end=5)
        assert lines == ["Line 5\n"]

    def test_read_lines_all(self, handler: FileSystemHandler, temp_file: Path):
        """Read all lines."""
        lines = handler.read_lines(temp_file, start=1, end=5)
        assert len(lines) == 5

    def test_read_lines_invalid_range_start_greater_than_end(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Error when start > end."""
        with pytest.raises(ValueError) as exc_info:
            handler.read_lines(temp_file, start=4, end=2)
        assert "start" in str(exc_info.value).lower()

    def test_read_lines_invalid_range_zero_start(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Error when start is 0 (1-based indexing)."""
        with pytest.raises(ValueError) as exc_info:
            handler.read_lines(temp_file, start=0, end=2)
        assert "1-based" in str(exc_info.value).lower() or "start" in str(
            exc_info.value
        ).lower()

    def test_read_lines_out_of_bounds(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Error when range exceeds file length."""
        with pytest.raises(ValueError) as exc_info:
            handler.read_lines(temp_file, start=1, end=100)
        assert "line" in str(exc_info.value).lower()

    def test_read_lines_file_not_found(
        self, handler: FileSystemHandler, tmp_path: Path
    ):
        """FileReadError for non-existent file."""
        with pytest.raises(FileReadError):
            handler.read_lines(tmp_path / "nonexistent.adoc", start=1, end=1)


# =============================================================================
# write_file() Tests - Atomic Write with Backup (ADR-004)
# =============================================================================


class TestWriteFile:
    """Tests for write_file() method with atomic backup strategy."""

    def test_write_file_success(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Successfully write file."""
        new_content = "New content\nSecond line\n"
        handler.write_file(temp_file, new_content)

        assert temp_file.read_text(encoding="utf-8") == new_content

    def test_write_file_creates_new(
        self, handler: FileSystemHandler, tmp_path: Path
    ):
        """Create new file if doesn't exist."""
        new_file = tmp_path / "new_file.adoc"
        handler.write_file(new_file, "Brand new content\n")

        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "Brand new content\n"

    def test_write_file_no_backup_remains(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """No .bak file remains after successful write."""
        handler.write_file(temp_file, "New content\n")

        backup_file = temp_file.with_suffix(temp_file.suffix + ".bak")
        assert not backup_file.exists()

    def test_write_file_no_tmp_remains(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """No .tmp file remains after successful write."""
        handler.write_file(temp_file, "New content\n")

        tmp_file = temp_file.with_suffix(temp_file.suffix + ".tmp")
        assert not tmp_file.exists()

    def test_write_file_utf8(self, handler: FileSystemHandler, tmp_path: Path):
        """Write file with UTF-8 characters."""
        file_path = tmp_path / "utf8_write.adoc"
        content = "Ümläuts: äöü ß\nEmoji: 🎉\n"

        handler.write_file(file_path, content)

        assert file_path.read_text(encoding="utf-8") == content

    def test_write_file_preserves_original_on_error(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Original file unchanged if write fails (simulated)."""
        original_content = temp_file.read_text(encoding="utf-8")

        # Make parent directory read-only to simulate write failure
        # This test is OS-dependent; skip if we can't make it read-only
        parent = temp_file.parent
        try:
            os.chmod(parent, 0o555)
            new_file = parent / "new_file.adoc"
            with pytest.raises(FileWriteError):
                handler.write_file(new_file, "Should fail\n")
        finally:
            os.chmod(parent, 0o755)

        # Original should be unchanged
        assert temp_file.read_text(encoding="utf-8") == original_content

    def test_write_file_permission_denied(
        self, handler: FileSystemHandler, tmp_path: Path
    ):
        """FileWriteError for permission denied."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o555)

        try:
            with pytest.raises(FileWriteError) as exc_info:
                handler.write_file(readonly_dir / "test.adoc", "content")
            assert "permission" in str(exc_info.value).lower()
        finally:
            os.chmod(readonly_dir, 0o755)


# =============================================================================
# update_section() Tests
# =============================================================================


class TestUpdateSection:
    """Tests for update_section() method."""

    def test_update_section_middle(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update middle section of file."""
        handler.update_section(
            temp_file, start_line=2, end_line=4, new_content="New Line 2\nNew Line 3\n"
        )

        content = temp_file.read_text(encoding="utf-8")
        assert content == "Line 1\nNew Line 2\nNew Line 3\nLine 5\n"

    def test_update_section_first_line(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update first line."""
        handler.update_section(temp_file, start_line=1, end_line=1, new_content="New First Line\n")

        content = temp_file.read_text(encoding="utf-8")
        assert content.startswith("New First Line\n")
        assert "Line 2" in content

    def test_update_section_last_line(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update last line."""
        handler.update_section(temp_file, start_line=5, end_line=5, new_content="New Last Line\n")

        content = temp_file.read_text(encoding="utf-8")
        assert content.endswith("New Last Line\n")
        assert "Line 4" in content

    def test_update_section_expand(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update section with more lines than original."""
        handler.update_section(
            temp_file,
            start_line=2,
            end_line=2,
            new_content="New Line 2a\nNew Line 2b\nNew Line 2c\n",
        )

        lines = temp_file.read_text(encoding="utf-8").splitlines(keepends=True)
        assert len(lines) == 7  # Was 5, replaced 1 with 3

    def test_update_section_shrink(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update section with fewer lines than original."""
        handler.update_section(
            temp_file, start_line=2, end_line=4, new_content="Single replacement\n"
        )

        lines = temp_file.read_text(encoding="utf-8").splitlines(keepends=True)
        assert len(lines) == 3  # Was 5, replaced 3 with 1

    def test_update_section_invalid_range(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Error for invalid line range."""
        with pytest.raises(ValueError):
            handler.update_section(temp_file, start_line=4, end_line=2, new_content="content")

    def test_update_section_out_of_bounds(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Error when range exceeds file."""
        with pytest.raises(ValueError):
            handler.update_section(temp_file, start_line=1, end_line=100, new_content="content")

    def test_update_section_atomic(
        self, handler: FileSystemHandler, temp_file: Path
    ):
        """Update is atomic - no .bak or .tmp files remain."""
        handler.update_section(temp_file, start_line=2, end_line=3, new_content="Updated\n")

        backup_file = temp_file.with_suffix(temp_file.suffix + ".bak")
        tmp_file = temp_file.with_suffix(temp_file.suffix + ".tmp")

        assert not backup_file.exists()
        assert not tmp_file.exists()

    def test_update_section_file_not_found(
        self, handler: FileSystemHandler, tmp_path: Path
    ):
        """FileReadError for non-existent file."""
        with pytest.raises(FileReadError):
            handler.update_section(
                tmp_path / "nonexistent.adoc",
                start_line=1,
                end_line=1,
                new_content="content",
            )


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_file_without_trailing_newline(
        self, handler: FileSystemHandler, temp_file_no_newline: Path
    ):
        """Handle file without trailing newline."""
        content = handler.read_file(temp_file_no_newline)
        assert content == "Line 1\nLine 2\nLine 3"

    def test_update_adds_newline_if_missing(
        self, handler: FileSystemHandler, temp_file_no_newline: Path
    ):
        """Update content without trailing newline."""
        handler.update_section(
            temp_file_no_newline,
            start_line=2,
            end_line=2,
            new_content="New Line 2\n",
        )

        content = temp_file_no_newline.read_text(encoding="utf-8")
        # Should have Line 1, New Line 2, Line 3
        assert "Line 1\n" in content
        assert "New Line 2\n" in content

    def test_path_as_string(self, handler: FileSystemHandler, temp_file: Path):
        """Accept path as string."""
        content = handler.read_file(str(temp_file))
        assert "Line 1" in content

    def test_concurrent_safety_note(self):
        """Document that concurrent access is not safe.

        Note: FileSystemHandler is not designed for concurrent access
        to the same file. External locking should be used if needed.
        """
        # This is a documentation test - no assertion needed
        pass
