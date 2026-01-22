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
