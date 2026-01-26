"""Tests for Issue #193, #194, #197: Edit operation bugs.

Tests fix for:
- #193: Encoding problem with umlauts in edit operations
- #194: Missing blank lines after edit operations
- #197: insert with --position append inserts at beginning
"""

from pathlib import Path

import pytest

from dacli.cli import _process_escape_sequences


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    from click.testing import CliRunner

    from dacli.cli import cli

    runner = CliRunner()

    class Runner:
        def invoke(self, args):
            return runner.invoke(cli, args)

    return Runner()


class TestEncodingFix193:
    """Tests for Issue #193: Encoding problem with umlauts."""

    def test_process_escape_sequences_preserves_umlauts(self):
        """Test that umlauts are preserved when processing escape sequences."""
        # Test German umlauts
        content = "Über uns äöü ß"
        result = _process_escape_sequences(content)
        assert result == "Über uns äöü ß"

    def test_process_escape_sequences_handles_newlines(self):
        """Test that \\n is correctly converted to newline."""
        content = "Line 1\\nLine 2"
        result = _process_escape_sequences(content)
        assert result == "Line 1\nLine 2"

    def test_process_escape_sequences_handles_tabs(self):
        """Test that \\t is correctly converted to tab."""
        content = "Column1\\tColumn2"
        result = _process_escape_sequences(content)
        assert result == "Column1\tColumn2"

    def test_process_escape_sequences_handles_mixed(self):
        """Test that umlauts and escape sequences work together."""
        content = "Über\\nÜber uns"
        result = _process_escape_sequences(content)
        assert result == "Über\nÜber uns"

    def test_process_escape_sequences_handles_literal_backslash(self):
        """Test that \\\\ is correctly converted to single backslash."""
        content = "Path\\\\to\\\\file"
        result = _process_escape_sequences(content)
        assert result == "Path\\to\\file"

    def test_process_escape_sequences_complex_case(self):
        """Test complex case with umlauts, newlines, and literal backslashes."""
        content = "Über\\nZeile 2\\t\\\\path"
        result = _process_escape_sequences(content)
        assert result == "Über\nZeile 2\t\\path"


class TestBlankLinesFix194:
    """Tests for Issue #194: Missing blank lines after edit operations."""

    def test_update_preserves_blank_lines(self, tmp_path, cli_runner):
        """Test that update operation preserves blank lines between sections."""
        # Create test file with proper spacing
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Test

== Section 1

Original content

== Section 2

More content
""")

        # Update Section 1
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "update", "test:section-1",
            "--content", "New content"
        ])

        assert result.exit_code == 0

        # Check that blank line is preserved after Section 1
        updated_content = test_file.read_text()
        lines = updated_content.split("\n")

        # Find Section 1
        section1_idx = next(i for i, line in enumerate(lines) if "Section 1" in line)
        # Find Section 2
        section2_idx = next(i for i, line in enumerate(lines) if "Section 2" in line)

        # There should be at least one blank line between sections
        between_sections = lines[section1_idx + 1:section2_idx]
        non_empty_lines = [line for line in between_sections if line.strip()]

        # Should have content + blank line
        assert any(line.strip() == "" for line in between_sections), \
            "No blank line found between sections"

    def test_insert_preserves_blank_lines(self, tmp_path, cli_runner):
        """Test that insert operation preserves blank lines."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Test

== Section 1

Content 1

== Section 2

Content 2
""")

        # Insert after Section 1
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "insert", "test:section-1",
            "--position", "after",
            "--content", "== New Section\\n\\nNew content"
        ])

        assert result.exit_code == 0

        # Check formatting
        updated_content = test_file.read_text()
        # Should have proper spacing
        assert "\n\n" in updated_content


class TestAppendPositionFix197:
    """Tests for Issue #197: append inserts at beginning instead of end."""

    def test_append_inserts_at_end(self, tmp_path, cli_runner):
        """Test that append position inserts at the END of the document."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Test Document

== Section 1

Content 1

== Section 2

Content 2
""")

        # Append to root document
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "insert", "test",
            "--position", "append",
            "--content", "== Appendix\\n\\nThis should be at the end"
        ])

        assert result.exit_code == 0

        # Check that Appendix is at the END
        updated_content = test_file.read_text()
        lines = updated_content.split("\n")

        # Find positions
        section2_idx = next(i for i, line in enumerate(lines) if "Section 2" in line)
        appendix_idx = next((i for i, line in enumerate(lines) if "Appendix" in line), None)

        assert appendix_idx is not None, "Appendix not found in document"
        assert appendix_idx > section2_idx, \
            f"Appendix at line {appendix_idx} should be AFTER Section 2 at line {section2_idx}"

    def test_append_to_section_with_children(self, tmp_path, cli_runner):
        """Test append to section that has child sections."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Test

== Parent Section

Parent content

=== Child 1

Child content 1

=== Child 2

Child content 2

== Another Section

Other content
""")

        # Append to Parent Section (should go after all children)
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "insert", "test:parent-section",
            "--position", "append",
            "--content", "=== Child 3\\n\\nNew child at the end"
        ])

        assert result.exit_code == 0

        updated_content = test_file.read_text()
        lines = updated_content.split("\n")

        # Find positions
        child2_idx = next(i for i, line in enumerate(lines) if "Child 2" in line)
        child3_idx = next((i for i, line in enumerate(lines) if "Child 3" in line), None)
        another_idx = next(i for i, line in enumerate(lines) if "Another Section" in line)

        assert child3_idx is not None, "Child 3 not found"
        assert child2_idx < child3_idx < another_idx, \
            "Child 3 should be after Child 2 but before Another Section"


class TestCombinedBugFixes:
    """Integration tests combining all three bug fixes."""

    def test_update_with_umlauts_and_blank_lines(self, tmp_path, cli_runner):
        """Test update with umlauts preserves both encoding and blank lines."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Test

== Einführung

Original

== Kapitel 2

Content
""")

        # Update with umlauts
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "update", "test:einführung",
            "--content", "Über uns: äöü ß"
        ])

        assert result.exit_code == 0

        updated_content = test_file.read_text()

        # Check umlauts are preserved
        assert "Über uns: äöü ß" in updated_content

        # Check blank line exists
        lines = updated_content.split("\n")
        intro_idx = next(i for i, line in enumerate(lines) if "Einführung" in line)
        kap2_idx = next(i for i, line in enumerate(lines) if "Kapitel 2" in line)

        between = lines[intro_idx + 1:kap2_idx]
        assert any(line.strip() == "" for line in between)

    def test_append_with_umlauts_at_correct_position(self, tmp_path, cli_runner):
        """Test append with umlauts inserts at end with correct encoding."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("""= Dokument

== Kapitel 1

Inhalt
""")

        # Append with umlauts (path is based on filename, not title)
        result = cli_runner.invoke([
            "--docs-root", str(tmp_path),
            "insert", "test",
            "--position", "append",
            "--content", "== Anhang\\n\\nÜber dieses Dokument: äöü"
        ])

        assert result.exit_code == 0

        updated_content = test_file.read_text()

        # Check umlauts
        assert "Über dieses Dokument: äöü" in updated_content

        # Check position (after Kapitel 1)
        lines = updated_content.split("\n")
        kap1_idx = next(i for i, line in enumerate(lines) if "Kapitel 1" in line)
        anhang_idx = next((i for i, line in enumerate(lines) if "Anhang" in line), None)

        assert anhang_idx is not None
        assert anhang_idx > kap1_idx
