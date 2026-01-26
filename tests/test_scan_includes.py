"""Tests for Issue #184: Include scanner for duplicate prevention.

Tests the scan_includes() method that identifies which files are included
by others, preventing them from being parsed as separate root documents.
"""

import tempfile
from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser


class TestScanIncludes:
    """Tests for AsciidocStructureParser.scan_includes()"""

    def test_scan_includes_simple(self, tmp_path):
        """Test scanning a file with a simple include directive."""
        # Create included file
        included = tmp_path / "chapters" / "intro.adoc"
        included.parent.mkdir(parents=True)
        included.write_text("== Introduction\n\nContent here.")

        # Create main file with include
        main = tmp_path / "main.adoc"
        main.write_text("""= Main Document

include::chapters/intro.adoc[]
""")

        # Scan for includes
        included_files = AsciidocStructureParser.scan_includes(main)

        # Should find the included file (resolved to absolute path)
        assert len(included_files) == 1
        assert included.resolve() in included_files

    def test_scan_includes_multiple(self, tmp_path):
        """Test scanning a file with multiple include directives."""
        # Create included files
        intro = tmp_path / "intro.adoc"
        intro.write_text("== Introduction")
        setup = tmp_path / "setup.adoc"
        setup.write_text("== Setup")

        # Create main file with multiple includes
        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::intro.adoc[]

include::setup.adoc[]
""")

        included_files = AsciidocStructureParser.scan_includes(main)

        assert len(included_files) == 2
        assert intro.resolve() in included_files
        assert setup.resolve() in included_files

    def test_scan_includes_with_options(self, tmp_path):
        """Test that include options are ignored (only path matters)."""
        included = tmp_path / "chapter.adoc"
        included.write_text("== Chapter")

        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::chapter.adoc[lines=1..10]
include::chapter.adoc[tag=section1]
""")

        included_files = AsciidocStructureParser.scan_includes(main)

        # Should find the file once (deduplicated by set)
        assert len(included_files) == 1
        assert included.resolve() in included_files

    def test_scan_includes_relative_paths(self, tmp_path):
        """Test includes with relative paths (../)."""
        # Create structure:
        # tmp_path/
        #   shared/
        #     common.adoc
        #   docs/
        #     guide.adoc  (includes ../shared/common.adoc)
        shared = tmp_path / "shared" / "common.adoc"
        shared.parent.mkdir(parents=True)
        shared.write_text("== Common Content")

        guide = tmp_path / "docs" / "guide.adoc"
        guide.parent.mkdir(parents=True)
        guide.write_text("""= Guide

include::../shared/common.adoc[]
""")

        included_files = AsciidocStructureParser.scan_includes(guide)

        assert len(included_files) == 1
        assert shared.resolve() in included_files

    def test_scan_includes_conditional(self, tmp_path):
        """Test that conditional includes are still captured."""
        included = tmp_path / "web.adoc"
        included.write_text("== Web Content")

        main = tmp_path / "main.adoc"
        main.write_text("""= Main

ifdef::backend-html5[]
include::web.adoc[]
endif::[]
""")

        included_files = AsciidocStructureParser.scan_includes(main)

        # Conditional includes are still captured (safe approach)
        assert len(included_files) == 1
        assert included.resolve() in included_files

    def test_scan_includes_no_includes(self, tmp_path):
        """Test scanning a file with no includes returns empty set."""
        main = tmp_path / "main.adoc"
        main.write_text("""= Main Document

== Chapter 1

Some content.
""")

        included_files = AsciidocStructureParser.scan_includes(main)

        assert len(included_files) == 0

    def test_scan_includes_missing_file(self, tmp_path):
        """Test scanning a non-existent file returns empty set."""
        non_existent = tmp_path / "does_not_exist.adoc"

        included_files = AsciidocStructureParser.scan_includes(non_existent)

        # Should handle gracefully
        assert len(included_files) == 0

    def test_scan_includes_nonexistent_included_file(self, tmp_path):
        """Test that includes pointing to non-existent files are still captured.

        The scanner doesn't validate file existence - that's the parser's job.
        We just collect all include paths.
        """
        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::chapters/intro.adoc[]
include::does_not_exist.adoc[]
""")

        # Only create first included file
        intro = tmp_path / "chapters" / "intro.adoc"
        intro.parent.mkdir(parents=True)
        intro.write_text("== Intro")

        included_files = AsciidocStructureParser.scan_includes(main)

        # Should find both (scanner doesn't validate existence)
        assert len(included_files) == 2
        assert intro.resolve() in included_files
        # The non-existent file will also be in the set (parser handles this)

    def test_scan_includes_duplicate_includes(self, tmp_path):
        """Test that duplicate includes are deduplicated."""
        included = tmp_path / "common.adoc"
        included.write_text("== Common")

        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::common.adoc[]

== Chapter 1

include::common.adoc[]

== Chapter 2

include::common.adoc[]
""")

        included_files = AsciidocStructureParser.scan_includes(main)

        # Set should deduplicate
        assert len(included_files) == 1
        assert included.resolve() in included_files


class TestTransitiveIncludes:
    """Tests for transitive include detection (A includes B includes C)."""

    def test_scan_does_not_resolve_nested(self, tmp_path):
        """Test that scan_includes does NOT recursively scan included files.

        This is by design - nested resolution happens during full parsing.
        The scan is only used to identify files that should not be root documents.
        """
        # Create chain: main -> chapter -> section
        section = tmp_path / "section.adoc"
        section.write_text("=== Section")

        chapter = tmp_path / "chapter.adoc"
        chapter.write_text("""== Chapter

include::section.adoc[]
""")

        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::chapter.adoc[]
""")

        # Scan main file
        main_includes = AsciidocStructureParser.scan_includes(main)

        # Should only find direct includes, not transitive
        assert len(main_includes) == 1
        assert chapter.resolve() in main_includes
        assert section.resolve() not in main_includes

        # To find all transitively included files, need to scan each file
        all_included = set()
        all_included.update(main_includes)
        for inc_file in list(all_included):
            all_included.update(AsciidocStructureParser.scan_includes(inc_file))

        # Now we should have both
        assert chapter.resolve() in all_included
        assert section.resolve() in all_included
