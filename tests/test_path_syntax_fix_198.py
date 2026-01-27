"""Tests for Issue #198: Inconsistent path syntax in error messages.

These tests verify that error messages correctly normalize paths and provide
helpful hints when users use incorrect separator syntax.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.structure_index import StructureIndex


class TestPathNormalization:
    """Test path normalization helper function."""

    def test_normalize_path_with_single_colon_unchanged(self):
        """Path with single colon should remain unchanged."""
        path = "doc:section"
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == "doc:section"
        assert had_extra is False

    def test_normalize_path_with_dots_unchanged(self):
        """Path with dots for nested sections should remain unchanged."""
        path = "doc:section.subsection.detail"
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == "doc:section.subsection.detail"
        assert had_extra is False

    def test_normalize_path_converts_extra_colons_to_dots(self):
        """Path with multiple colons should have extras converted to dots."""
        path = "doc:section:subsection"
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == "doc:section.subsection"
        assert had_extra is True

    def test_normalize_path_with_three_colons(self):
        """Path with three colons should convert last two to dots."""
        path = "doc:section:subsection:detail"
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == "doc:section.subsection.detail"
        assert had_extra is True

    def test_normalize_path_no_colon(self):
        """Path without colon should remain unchanged."""
        path = "section.subsection"
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == "section.subsection"
        assert had_extra is False

    def test_normalize_path_empty_string(self):
        """Empty path should remain unchanged."""
        path = ""
        normalized, had_extra = StructureIndex.normalize_path(path)

        assert normalized == ""
        assert had_extra is False


class TestCLIErrorMessages:
    """Test CLI error messages for path syntax issues."""

    @pytest.fixture
    def temp_doc_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test documents."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text(
            """= Test Document

== Chapter 1

Content here.

=== Subsection

Nested content.
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_error_with_correct_syntax_no_hint(self, temp_doc_dir: Path):
        """Error for non-existent path with correct syntax shows no hint."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "section",
                "test:nonexistent",
            ],
        )

        assert result.exit_code != 0
        assert "PATH_NOT_FOUND" in result.output
        assert "test:nonexistent" in result.output
        # Should NOT have hint because syntax is correct
        assert "hint" not in result.output.lower()
        assert "Use colon" not in result.output

    def test_error_with_multiple_colons_shows_hint(self, temp_doc_dir: Path):
        """Error for path with multiple colons shows helpful hint (Issue #198)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "section",
                "test:chapter-1:subsection",  # WRONG - using colons for nested
            ],
        )

        assert result.exit_code != 0
        assert "PATH_NOT_FOUND" in result.output

        # Should show the malformed path
        assert "test:chapter-1:subsection" in result.output

        # Should show corrected path
        assert "test:chapter-1.subsection" in result.output

        # Should show helpful hint
        assert "hint" in result.output.lower() or "Hint" in result.output
        assert "Use colon (:) only once" in result.output
        assert "Use dots (.) for nested sections" in result.output

    def test_error_includes_corrected_path_field(self, temp_doc_dir: Path):
        """Error details should include corrected_path field when normalizing."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "--format",
                "json",
                "section",
                "test:a:b:c",
            ],
        )

        assert result.exit_code != 0

        # In JSON output, should have corrected_path field
        output = result.output
        assert "corrected_path" in output
        assert "test:a.b.c" in output

    def test_suggestions_use_correct_format(self, temp_doc_dir: Path):
        """Suggestions should use correct path format (colon + dots)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "section",
                "test:chapter-1:sub",  # Close to actual path
            ],
        )

        assert result.exit_code != 0

        # Suggestions should use correct format with dots
        assert "suggestions" in result.output.lower() or "test:chapter-1." in result.output


class TestPathFormatDocumentation:
    """Test that correct path format is consistently used."""

    def test_valid_path_with_colon_and_dots(self, tmp_path: Path):
        """Valid paths should use colon once and dots for nested."""
        doc_file = tmp_path / "doc.adoc"
        doc_file.write_text(
            """= Document

== Section

=== Subsection

Content.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(tmp_path),
                "section",
                "doc:section.subsection",  # Correct format
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Content." in result.output or "Subsection" in result.output
