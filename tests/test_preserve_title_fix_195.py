"""Tests for Issue #195: --no-preserve-title validation.

These tests verify that preserve_title=False requires content to include a title
to prevent document structure corruption.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dacli.cli import cli
from dacli.file_handler import FileSystemHandler
from dacli.services.content_service import update_section as service_update_section
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test documents."""
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Test Document

== Section 1

Original content of section 1.

== Section 2

Original content of section 2.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def index_and_handler(temp_doc_dir: Path):
    """Create index and file handler for tests."""
    from dacli.asciidoc_parser import AsciidocStructureParser

    parser = AsciidocStructureParser(base_path=temp_doc_dir)
    index = StructureIndex()
    file_handler = FileSystemHandler()

    # Parse and index the test documents
    documents = []
    for doc_file in temp_doc_dir.glob("*.adoc"):
        doc = parser.parse_file(doc_file)
        documents.append(doc)

    index.build_from_documents(documents)

    return index, file_handler


class TestPreserveTitleFalseValidation:
    """Test validation when preserve_title=False."""

    def test_preserve_title_false_with_title_succeeds(
        self, index_and_handler, temp_doc_dir: Path
    ):
        """preserve_title=False WITH title in content should succeed."""
        index, file_handler = index_and_handler

        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="== New Title\n\nNew content with new title.",
            preserve_title=False,
        )

        assert result["success"] is True
        assert "error" not in result

        # Verify the new title is in the file
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== New Title" in file_content
        assert "New content with new title." in file_content
        assert "== Section 1" not in file_content  # Old title should be gone

    def test_preserve_title_false_without_title_fails(
        self, index_and_handler, temp_doc_dir: Path
    ):
        """preserve_title=False WITHOUT title in content should fail (Issue #195)."""
        index, file_handler = index_and_handler

        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="New content without title",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "error" in result
        assert "must include a section title" in result["error"]
        assert "preserve_title is false" in result["error"]

        # Verify the original content is unchanged
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Section 1" in file_content
        assert "Original content of section 1." in file_content

    def test_preserve_title_false_with_markdown_style_heading(
        self, index_and_handler, temp_doc_dir: Path
    ):
        """preserve_title=False with Markdown-style heading (##) should succeed."""
        index, file_handler = index_and_handler

        # Test that Markdown-style headings are also accepted (# instead of =)
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="## New Markdown-Style Title\n\nNew content.",
            preserve_title=False,
        )

        assert result["success"] is True
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "## New Markdown-Style Title" in file_content

    def test_preserve_title_false_with_only_whitespace_fails(
        self, index_and_handler
    ):
        """preserve_title=False with only whitespace should fail."""
        index, file_handler = index_and_handler

        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="   \n\n   ",
            preserve_title=False,
        )

        assert result["success"] is False
        assert "must include a section title" in result["error"]

    def test_preserve_title_true_without_title_succeeds(
        self, index_and_handler, temp_doc_dir: Path
    ):
        """preserve_title=True (default) WITHOUT title should succeed (existing behavior)."""
        index, file_handler = index_and_handler

        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path="test:section-1",
            content="New content without explicit title",
            preserve_title=True,  # Default
        )

        assert result["success"] is True

        # Verify the original title is preserved
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Section 1" in file_content
        assert "New content without explicit title" in file_content


class TestCLINoPreserveTitleFlag:
    """Test CLI --no-preserve-title flag."""

    def test_cli_no_preserve_title_with_title_succeeds(self, temp_doc_dir: Path):
        """CLI --no-preserve-title WITH title should succeed."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:section-1",
                "--content",
                "== CLI New Title\\n\\nNew content from CLI.",
                "--no-preserve-title",
            ],
        )

        assert result.exit_code == 0
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== CLI New Title" in file_content

    def test_cli_no_preserve_title_without_title_fails(self, temp_doc_dir: Path):
        """CLI --no-preserve-title WITHOUT title should fail (Issue #195)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:section-1",
                "--content",
                "New content without title",
                "--no-preserve-title",
            ],
        )

        assert result.exit_code != 0
        assert "must include a section title" in result.output

        # Verify original content unchanged
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Section 1" in file_content
        assert "Original content of section 1." in file_content

    def test_cli_default_preserves_title(self, temp_doc_dir: Path):
        """CLI without --no-preserve-title should preserve title (default)."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root",
                str(temp_doc_dir),
                "update",
                "test:section-1",
                "--content",
                "Content without title",
            ],
        )

        assert result.exit_code == 0
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Section 1" in file_content  # Original title preserved
        assert "Content without title" in file_content
