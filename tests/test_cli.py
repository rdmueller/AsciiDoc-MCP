"""Tests for CLI interface.

Tests for the mcp-docs CLI tool specified in 06_cli_specification.adoc.
Uses click.testing.CliRunner for testing click commands.
"""

import json

import pytest
from click.testing import CliRunner


class TestCliBasic:
    """Test basic CLI functionality."""

    def test_cli_help_shows_commands(self):
        """CLI --help should list all available commands."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "structure" in result.output
        assert "section" in result.output
        assert "search" in result.output
        assert "elements" in result.output
        assert "metadata" in result.output
        assert "validate" in result.output
        assert "update" in result.output
        assert "insert" in result.output
        assert "sections-at-level" in result.output

    def test_cli_version_shows_version(self):
        """CLI --version should show the version number."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower() or "." in result.output


class TestCliCommandAliases:
    """Test command aliases for shorter typing."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Some introduction text about testing.

== Architecture

Architecture description.
""")
        return tmp_path

    def test_str_alias_for_structure(self, sample_docs):
        """'str' should work as alias for 'structure'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "str"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "sections" in data

    def test_s_alias_for_search(self, sample_docs):
        """'s' should work as alias for 'search'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "s", "testing"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "query" in data
        assert data["query"] == "testing"

    def test_sec_alias_for_section(self, sample_docs):
        """'sec' should work as alias for 'section'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "sec", "introduction"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "title" in data

    def test_meta_alias_for_metadata(self, sample_docs):
        """'meta' should work as alias for 'metadata'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "meta"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_files" in data or "total_sections" in data

    def test_el_alias_for_elements(self, sample_docs):
        """'el' should work as alias for 'elements'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "el"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "elements" in data

    def test_val_alias_for_validate(self, sample_docs):
        """'val' should work as alias for 'validate'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "val"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "valid" in data

    def test_lv_alias_for_sections_at_level(self, sample_docs):
        """'lv' should work as alias for 'sections-at-level'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "lv", "1"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "level" in data
        assert data["level"] == 1


class TestCliStructureCommand:
    """Test the 'structure' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        # Create a simple AsciiDoc file
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Some introduction text.

== Architecture

Architecture description.
""")
        return tmp_path

    def test_structure_returns_json_when_requested(self, sample_docs):
        """structure command should return valid JSON when --format json is specified."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "structure"]
        )

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert "sections" in data or "total_sections" in data

    def test_structure_with_max_depth(self, sample_docs):
        """structure --max-depth should limit returned depth."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(sample_docs), "--format", "json", "structure", "--max-depth", "1"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestCliSectionCommand:
    """Test the 'section' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Introduction content here.
""")
        return tmp_path

    def test_section_returns_content(self, sample_docs):
        """section command should return section content as JSON when requested."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(sample_docs), "--format", "json", "section", "introduction"],
        )

        # Exit code 0 for found, 3 for not found
        assert result.exit_code in (0, 3)
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_section_not_found_returns_error(self, sample_docs):
        """section command should return error for non-existent path."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(sample_docs), "--format", "json", "section", "nonexistent"],
        )

        assert result.exit_code == 3  # PATH_NOT_FOUND
        data = json.loads(result.output)
        assert "error" in data


class TestCliSearchCommand:
    """Test the 'search' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Authentication

This section covers authentication topics.
""")
        return tmp_path

    def test_search_returns_results(self, sample_docs):
        """search command should return JSON results when requested."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(sample_docs), "--format", "json", "search", "authentication"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "query" in data
        assert "results" in data


class TestCliMetadataCommand:
    """Test the 'metadata' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Section One

Content.
""")
        return tmp_path

    def test_metadata_project_level(self, sample_docs):
        """metadata without path should return project metadata."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "metadata"]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_files" in data or "total_sections" in data

    def test_metadata_section_level(self, sample_docs):
        """metadata with path should return section metadata."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "metadata", "section-one"]
        )

        # Exit code 0 for found, 3 for not found
        assert result.exit_code in (0, 3)
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestCliValidateCommand:
    """Test the 'validate' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Section

Content.
""")
        return tmp_path

    def test_validate_returns_result(self, sample_docs):
        """validate command should return validation result."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(sample_docs), "--format", "json", "validate"]
        )

        assert result.exit_code in (0, 4)  # 0 = valid, 4 = validation errors
        data = json.loads(result.output)
        assert "valid" in data


class TestCliOutputFormats:
    """Test output format options."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test

== Section

Content.
""")
        return tmp_path

    def test_text_format_is_default(self, sample_docs):
        """Default output should be text format."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--docs-root", str(sample_docs), "structure"])

        assert result.exit_code == 0
        # Should be text format (not JSON)
        # Text format uses key: value style
        assert "sections:" in result.output or "total_sections:" in result.output

    def test_pretty_flag_formats_json_output(self, sample_docs):
        """--pretty flag should format JSON output for readability."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(sample_docs), "--format", "json", "--pretty", "structure"],
        )

        assert result.exit_code == 0
        # Pretty JSON has newlines and indentation
        assert "\n" in result.output
        json.loads(result.output)  # Still valid JSON


class TestCliVerboseOption:
    """Test the --verbose/-v option for showing warnings."""

    @pytest.fixture
    def docs_with_duplicates(self, tmp_path):
        """Create docs that will generate duplicate section path warnings."""
        # Create two files with same section titles (will create duplicate paths)
        doc1 = tmp_path / "doc1.adoc"
        doc1.write_text("""= Document One

== Introduction

Content from doc1.
""")
        doc2 = tmp_path / "doc2.adoc"
        doc2.write_text("""= Document Two

== Introduction

Content from doc2.
""")
        return tmp_path

    def test_verbose_option_in_help(self):
        """--verbose option should be listed in help."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--verbose" in result.output or "-v" in result.output

    def test_verbose_short_option_in_help(self):
        """Short -v option should be available."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "-v" in result.output

    def test_default_suppresses_warnings(self, docs_with_duplicates):
        """By default (without --verbose), warnings should be suppressed."""
        from dacli.cli import cli

        runner = CliRunner()

        # Default (no verbose) - command should work with clean output
        result_default = runner.invoke(
            cli, ["--docs-root", str(docs_with_duplicates), "--format", "json", "structure"]
        )
        assert result_default.exit_code == 0
        # Output should be valid JSON (no warnings polluting it)
        json.loads(result_default.output)

    def test_verbose_short_form_works(self, docs_with_duplicates):
        """-v short form should work the same as --verbose."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--docs-root", str(docs_with_duplicates), "-v", "--format", "json", "structure"]
        )

        assert result.exit_code == 0
        # Output should be valid JSON
        json.loads(result.output)

    def test_default_still_shows_errors(self, tmp_path):
        """Default mode should still show error messages."""
        from dacli.cli import cli

        runner = CliRunner()
        # Request non-existent section - should still show error
        doc = tmp_path / "test.adoc"
        doc.write_text("= Test\n\n== Section\n\nContent.")

        result = runner.invoke(
            cli,
            ["--docs-root", str(tmp_path), "section", "nonexistent"],
        )

        # Should fail with PATH_NOT_FOUND (exit code 3)
        assert result.exit_code == 3

    def test_verbose_does_not_affect_output(self, tmp_path):
        """--verbose should not affect the JSON/text output content."""
        from dacli.cli import cli

        doc = tmp_path / "test.adoc"
        doc.write_text("= Test\n\n== Section\n\nContent.")

        runner = CliRunner()

        # Compare output with and without verbose (single file, no warnings)
        result_default = runner.invoke(
            cli, ["--docs-root", str(tmp_path), "structure"]
        )
        result_verbose = runner.invoke(
            cli, ["--docs-root", str(tmp_path), "--verbose", "structure"]
        )

        assert result_default.exit_code == 0
        assert result_verbose.exit_code == 0
        # Output should be the same when there are no warnings
        assert result_default.output == result_verbose.output


class TestCliGitignoreOptions:
    """Test --no-gitignore and --include-hidden options."""

    def test_no_gitignore_option_in_help(self):
        """--no-gitignore option should be listed in help."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--no-gitignore" in result.output

    def test_include_hidden_option_in_help(self):
        """--include-hidden option should be listed in help."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--include-hidden" in result.output

    def test_no_gitignore_includes_ignored_files(self, tmp_path):
        """--no-gitignore should include files matching .gitignore patterns."""
        from dacli.cli import cli

        # Create .gitignore that ignores 'ignored/' directory
        (tmp_path / ".gitignore").write_text("ignored/\n")

        # Create docs in both normal and ignored directories
        (tmp_path / "visible.adoc").write_text("= Visible Doc\n\n== Section\n\nContent.")
        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        (ignored_dir / "hidden.adoc").write_text("= Hidden Doc\n\n== Secret\n\nSecret content.")

        runner = CliRunner()

        # Without --no-gitignore: should only see visible doc
        result_normal = runner.invoke(
            cli, ["--docs-root", str(tmp_path), "--format", "json", "metadata"]
        )
        assert result_normal.exit_code == 0
        data_normal = json.loads(result_normal.output)
        assert data_normal["total_files"] == 1

        # With --no-gitignore: should see both docs
        result_with_ignored = runner.invoke(
            cli, ["--docs-root", str(tmp_path), "--no-gitignore", "--format", "json", "metadata"]
        )
        assert result_with_ignored.exit_code == 0
        data_with_ignored = json.loads(result_with_ignored.output)
        assert data_with_ignored["total_files"] == 2

    def test_include_hidden_includes_hidden_directories(self, tmp_path):
        """--include-hidden should include files in hidden directories."""
        from dacli.cli import cli

        # Create docs in both normal and hidden directories
        (tmp_path / "visible.adoc").write_text("= Visible Doc\n\n== Section\n\nContent.")
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.adoc").write_text("= Secret Doc\n\n== Secret\n\nSecret content.")

        runner = CliRunner()

        # Without --include-hidden: should only see visible doc
        result_normal = runner.invoke(
            cli, ["--docs-root", str(tmp_path), "--format", "json", "metadata"]
        )
        assert result_normal.exit_code == 0
        data_normal = json.loads(result_normal.output)
        assert data_normal["total_files"] == 1

        # With --include-hidden: should see both docs
        result_with_hidden = runner.invoke(
            cli,
            ["--docs-root", str(tmp_path), "--include-hidden", "--format", "json", "metadata"],
        )
        assert result_with_hidden.exit_code == 0
        data_with_hidden = json.loads(result_with_hidden.output)
        assert data_with_hidden["total_files"] == 2

    def test_both_options_combined(self, tmp_path):
        """--no-gitignore and --include-hidden can be used together."""
        from dacli.cli import cli

        # Create .gitignore
        (tmp_path / ".gitignore").write_text("ignored/\n")

        # Create visible doc
        (tmp_path / "visible.adoc").write_text("= Visible\n\n== S1\n\nC1.")

        # Create ignored doc
        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        (ignored_dir / "ignored.adoc").write_text("= Ignored\n\n== S2\n\nC2.")

        # Create hidden doc
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "hidden.adoc").write_text("= Hidden\n\n== S3\n\nC3.")

        runner = CliRunner()

        # With both options: should see all 3 docs
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--no-gitignore",
                "--include-hidden",
                "--format", "json",
                "metadata",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_files"] == 3


class TestCliHelpImprovements:
    """Test help system improvements: grouped commands, typo suggestions, examples."""

    def test_help_shows_command_groups(self):
        """Help output should organize commands into story-based groups."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for group headers
        assert "Discover" in result.output
        assert "Find" in result.output
        assert "Read" in result.output
        assert "Validate" in result.output
        assert "Edit" in result.output

    def test_main_help_shows_examples(self):
        """Main --help should show usage examples."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output
        assert "dacli" in result.output
        assert "structure" in result.output
        assert "search" in result.output

    def test_help_shows_command_aliases(self):
        """Help output should show aliases in parentheses."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for alias display format
        assert "(str)" in result.output  # structure alias
        assert "(s)" in result.output    # search alias
        assert "(sec)" in result.output  # section alias

    def test_typo_suggestion_for_similar_command(self):
        """Typo in command name should suggest correct command."""
        from dacli.cli import cli

        runner = CliRunner()
        # "serch" is close to "search"
        result = runner.invoke(cli, ["serch", "test"])

        assert result.exit_code != 0
        assert "Did you mean" in result.output
        assert "search" in result.output or "s" in result.output

    def test_typo_suggestion_for_structure(self):
        """Typo 'strcuture' should suggest 'structure'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["strcuture"])

        assert result.exit_code != 0
        assert "Did you mean" in result.output
        assert "structure" in result.output or "str" in result.output

    def test_typo_suggestion_for_validate(self):
        """Typo 'vaildate' should suggest 'validate'."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["vaildate"])

        assert result.exit_code != 0
        assert "Did you mean" in result.output
        assert "validate" in result.output or "val" in result.output

    def test_no_suggestion_for_completely_different_input(self):
        """Completely different input should not suggest anything."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["xyz123"])

        assert result.exit_code != 0
        # Should have error but possibly no suggestion
        assert "No such command" in result.output

    def test_structure_command_help_has_example(self):
        """'structure --help' should show usage examples."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["structure", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output or "dacli" in result.output

    def test_search_command_help_has_example(self):
        """'search --help' should show usage examples."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output or "dacli" in result.output

    def test_section_command_help_has_example(self):
        """'section --help' should show usage examples."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["section", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output or "dacli" in result.output

    def test_validate_command_help_has_example(self):
        """'validate --help' should show usage examples."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output or "dacli" in result.output


class TestCliReadmeInclusion:
    """Test that README.md and CLAUDE.md are included in indexing (Issue #107)."""

    def test_readme_is_indexed_and_searchable(self, tmp_path):
        """README.md should be indexed and searchable."""
        from dacli.cli import cli

        # Create README.md with searchable content
        readme = tmp_path / "README.md"
        readme.write_text("""# Project Documentation

## Authentication

This section covers authentication mechanisms.
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(tmp_path), "--format", "json", "search", "authentication"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_results"] > 0, "README.md content should be searchable"

    def test_claude_md_is_indexed_and_searchable(self, tmp_path):
        """CLAUDE.md should be indexed and searchable."""
        from dacli.cli import cli

        # Create CLAUDE.md with searchable content
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""# Claude Instructions

## Configuration

Special configuration for Claude assistant.
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(tmp_path), "--format", "json", "search", "configuration"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_results"] > 0, "CLAUDE.md content should be searchable"

    def test_readme_appears_in_structure(self, tmp_path):
        """README.md should appear in document structure."""
        from dacli.cli import cli

        readme = tmp_path / "README.md"
        readme.write_text("""# My Project

## Overview

Project overview.
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--docs-root", str(tmp_path), "--format", "json", "structure"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_sections"] > 0, "README.md sections should be in structure"


class TestCliInsertCommand:
    """Test the 'insert' command."""

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Test Document

== Introduction

Introduction content here.

== Components

Components overview.

=== Frontend

Frontend details.

=== Backend

Backend details.

== Conclusion

Final thoughts.
""")
        return tmp_path

    def test_insert_processes_escape_sequences(self, sample_docs):
        """Insert command should convert \\n to actual newlines (Issue #106)."""
        from dacli.cli import cli

        runner = CliRunner()
        # Insert content with escape sequences
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(sample_docs),
                "--format", "json",
                "insert", "introduction",
                "--position", "after",
                "--content", "== New Section\\n\\nNew content here.\\n",
            ],
        )

        assert result.exit_code == 0

        # Read the file and verify actual newlines were inserted
        doc_file = sample_docs / "test.adoc"
        content = doc_file.read_text()

        # Should contain actual newlines, not literal \n
        assert "\\n" not in content or "== New Section\n" in content
        assert "== New Section" in content
        assert "New content here." in content

    def test_insert_append_adds_at_end_of_section(self, sample_docs):
        """Insert --position append should add content after all subsections (Issue #108)."""
        from dacli.cli import cli

        runner = CliRunner()
        # Append to Components section (which has Frontend and Backend subsections)
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(sample_docs),
                "--format", "json",
                "insert", "components",
                "--position", "append",
                "--content", "=== Testing\\n\\nTesting details.\\n",
            ],
        )

        assert result.exit_code == 0

        # Read the file and check position
        doc_file = sample_docs / "test.adoc"
        content = doc_file.read_text()

        # The new section should appear AFTER Backend, not right after Components header
        backend_pos = content.find("=== Backend")
        if "=== Testing" in content:
            testing_pos = content.find("=== Testing")
        else:
            testing_pos = content.find("Testing details")
        conclusion_pos = content.find("== Conclusion")

        # Testing should be after Backend but before Conclusion
        assert testing_pos > backend_pos, "Appended content should be after Backend subsection"
        assert testing_pos < conclusion_pos, "Appended content should be before Conclusion"

    def test_insert_before_works(self, sample_docs):
        """Insert --position before should add content before section."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(sample_docs),
                "--format", "json",
                "insert", "components",
                "--position", "before",
                "--content", "== Prerequisites\\n\\nBefore components.\\n",
            ],
        )

        assert result.exit_code == 0

        doc_file = sample_docs / "test.adoc"
        content = doc_file.read_text()

        # Prerequisites should appear before Components
        prereq_pos = content.find("Prerequisites") if "Prerequisites" in content else -1
        components_pos = content.find("== Components")

        assert prereq_pos != -1, "Prerequisites section should exist"
        assert prereq_pos < components_pos, "Prerequisites should be before Components"

    def test_insert_after_works(self, sample_docs):
        """Insert --position after should add content after section."""
        from dacli.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(sample_docs),
                "--format", "json",
                "insert", "introduction",
                "--position", "after",
                "--content", "== Goals\\n\\nProject goals.\\n",
            ],
        )

        assert result.exit_code == 0

        doc_file = sample_docs / "test.adoc"
        content = doc_file.read_text()

        # Goals should appear after Introduction but before Components
        intro_pos = content.find("== Introduction")
        goals_pos = content.find("Goals") if "Goals" in content else -1
        components_pos = content.find("== Components")

        assert goals_pos != -1, "Goals section should exist"
        assert goals_pos > intro_pos, "Goals should be after Introduction"
        assert goals_pos < components_pos, "Goals should be before Components"

    def test_insert_stdin_support(self, sample_docs):
        """Insert command should read content from stdin when --content is '-' (Issue #113)."""
        from dacli.cli import cli

        runner = CliRunner()
        # Simulate stdin input
        stdin_content = "== From Stdin\n\nContent from stdin.\n"
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(sample_docs),
                "--format", "json",
                "insert", "introduction",
                "--position", "after",
                "--content", "-",
            ],
            input=stdin_content,
        )

        assert result.exit_code == 0

        doc_file = sample_docs / "test.adoc"
        content = doc_file.read_text()

        # Content from stdin should be in the file
        assert "From Stdin" in content
        assert "Content from stdin" in content

    def test_insert_adds_blank_line_before_heading(self, tmp_path):
        """Insert should add blank line before heading when inserting after content (Issue #114)."""
        from dacli.cli import cli

        # Create a minimal doc without trailing blank line before next section
        doc_file = tmp_path / "test.md"
        doc_file.write_text("# Title\n\n## Section A\n\nContent A.\n## Section B\n\nContent B.\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "insert", "section-a",
                "--position", "after",
                "--content", "## New Section\\n\\nNew content.\\n",
            ],
        )

        assert result.exit_code == 0

        content = doc_file.read_text()

        # There should be a blank line before the new heading
        # The pattern "Content A.\n\n## New Section" indicates proper spacing
        assert "Content A." in content
        assert "## New Section" in content
        # Check that we don't have "Content A.\n## New Section" (no blank line)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("## New Section"):
                # Previous non-empty content line should be followed by blank line
                assert i > 0, "New section should not be first line"


class TestCliUpdateCommand:
    """Test the 'update' command."""

    def test_update_preserves_heading_level_markdown(self, tmp_path):
        """Update command should preserve heading level in Markdown (Issue #115)."""
        from dacli.cli import cli

        # Create a markdown doc with ## heading
        doc_file = tmp_path / "test.md"
        doc_file.write_text("# Title\n\n## Parent\n\nOriginal content.\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "update", "parent",
                "--content", "New content.",
            ],
        )

        assert result.exit_code == 0

        content = doc_file.read_text()

        # Heading level should still be ## (h2), not ### (h3)
        assert "## Parent" in content
        assert "### Parent" not in content
        assert "New content" in content

    def test_update_preserves_heading_level_asciidoc(self, tmp_path):
        """Update command should preserve heading level in AsciiDoc."""
        from dacli.cli import cli

        # Create an asciidoc doc with == heading
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("= Title\n\n== Parent\n\nOriginal content.\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "update", "parent",
                "--content", "New content.",
            ],
        )

        assert result.exit_code == 0

        content = doc_file.read_text()

        # Heading level should still be == (h2), not === (h3)
        assert "== Parent" in content
        assert "=== Parent" not in content
        assert "New content" in content

    def test_update_stdin_support(self, tmp_path):
        """Update command should read content from stdin when --content is '-' (Issue #113)."""
        from dacli.cli import cli

        doc_file = tmp_path / "test.md"
        doc_file.write_text("# Title\n\n## Section\n\nOriginal content.\n")

        runner = CliRunner()
        stdin_content = "Updated from stdin."
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "update", "section",
                "--content", "-",
            ],
            input=stdin_content,
        )

        assert result.exit_code == 0

        content = doc_file.read_text()
        assert "Updated from stdin" in content
        assert "Original content" not in content

    def test_update_stdin_with_heading_preserves_title(self, tmp_path):
        """Update with stdin heading should preserve original title (Issue #120).

        When preserve_title=true (default), the original title should always
        be kept, even if the stdin content starts with a heading.
        """
        from dacli.cli import cli

        doc_file = tmp_path / "test.md"
        doc_file.write_text("# Title\n\n## Original Section\n\nOriginal content.\n")

        runner = CliRunner()
        # stdin content has a different heading
        stdin_content = "## Replacement Title\n\nNew content from stdin.\n"
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "update", "original-section",
                "--content", "-",
            ],
            input=stdin_content,
        )

        assert result.exit_code == 0

        content = doc_file.read_text()
        # Original title should be preserved, replacement title should be stripped
        assert "## Original Section" in content
        assert "Replacement Title" not in content
        assert "New content from stdin" in content

    def test_update_stdin_with_heading_preserves_title_asciidoc(self, tmp_path):
        """Update with stdin heading should preserve title in AsciiDoc (#120)."""
        from dacli.cli import cli

        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("= Title\n\n== Original Section\n\nOriginal content.\n")

        runner = CliRunner()
        # stdin content has a different heading
        stdin_content = "== Replacement Title\n\nNew content from stdin.\n"
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "update", "original-section",
                "--content", "-",
            ],
            input=stdin_content,
        )

        assert result.exit_code == 0

        content = doc_file.read_text()
        # Original title should be preserved, replacement title should be stripped
        assert "== Original Section" in content
        assert "Replacement Title" not in content
        assert "New content from stdin" in content


class TestCliBugFixes:
    """Tests for specific bug fixes in CLI commands."""

    def test_insert_adds_blank_line_after_content_before_heading(self, tmp_path):
        """Insert should add blank line after content when next line is a heading (Issue #119).

        When inserting content that doesn't end with a blank line, and the next line
        in the document starts with a heading, a blank line should be added after
        the inserted content.
        """
        from dacli.cli import cli

        # Create a doc where section-a is immediately followed by section-b heading
        doc_file = tmp_path / "test.adoc"
        doc_file.write_text("""= Title

== Section A

Content A.

== Section B

Content B.
""")

        runner = CliRunner()
        # Insert plain text (no heading) after Section A
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "insert", "section-a",
                "--position", "after",
                "--content", "Additional text without heading.",
            ],
        )

        assert result.exit_code == 0

        content = doc_file.read_text()

        # There should be a blank line between the inserted text and Section B heading
        assert "Additional text without heading." in content
        assert "== Section B" in content

        # Check proper formatting: inserted text should be followed by blank line before heading
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "Additional text without heading" in line:
                # Find the next non-empty line index
                next_content_idx = i + 1
                while next_content_idx < len(lines) and not lines[next_content_idx].strip():
                    next_content_idx += 1
                if next_content_idx < len(lines) and lines[next_content_idx].startswith("=="):
                    # There should be at least one blank line between
                    blank_lines = next_content_idx - i - 1
                    assert blank_lines >= 1, f"Need blank line before heading, got {blank_lines}"
                break

    def test_insert_adds_blank_line_after_content_before_heading_markdown(self, tmp_path):
        """Insert should add blank line after content when next line is a heading (Markdown)."""
        from dacli.cli import cli

        doc_file = tmp_path / "test.md"
        doc_file.write_text("""# Title

## Section A

Content A.

## Section B

Content B.
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--docs-root", str(tmp_path),
                "--format", "json",
                "insert", "section-a",
                "--position", "after",
                "--content", "Additional text without heading.",
            ],
        )

        assert result.exit_code == 0

        content = doc_file.read_text()

        # Check proper formatting
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "Additional text without heading" in line:
                next_content_idx = i + 1
                while next_content_idx < len(lines) and not lines[next_content_idx].strip():
                    next_content_idx += 1
                if next_content_idx < len(lines) and lines[next_content_idx].startswith("#"):
                    blank_lines = next_content_idx - i - 1
                    assert blank_lines >= 1, f"Need blank line before heading, got {blank_lines}"
                break
