"""Integration tests for Issue #184: Included files should not appear as root documents.

Tests the full flow: finding files, scanning includes, filtering, parsing, indexing.
"""

import tempfile
from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.markdown_parser import MarkdownStructureParser
from dacli.mcp_app import _build_index
from dacli.structure_index import StructureIndex


class TestIncludedFilesNotInStructure:
    """Test that included files do not appear as separate root documents."""

    def test_included_file_not_in_structure(self, tmp_path):
        """Test that a file included by another does not appear in structure."""
        # Create structure:
        # arc42.adoc (root) -> includes chapters/01_intro.adoc
        # chapters/01_intro.adoc should NOT appear as root document

        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        intro = chapters_dir / "01_intro.adoc"
        intro.write_text("""== Introduction

This is the introduction chapter.

=== Goals

Our main goals are...
""")

        arc42 = tmp_path / "arc42.adoc"
        arc42.write_text("""= Architecture Documentation

include::chapters/01_intro.adoc[]

== Architecture Decisions

Some content here.
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        # Get all sections
        structure = index.get_structure()
        sections = structure["sections"]

        # Should have exactly ONE top-level section (Architecture Documentation)
        assert len(sections) == 1
        assert sections[0]["title"] == "Architecture Documentation"

        # The included "Introduction" section should be a child, not a root
        # Path should be "arc42:introduction" (prefixed with document name per ADR-008)
        intro_section = index.get_section("arc42:introduction")
        assert intro_section is not None
        assert intro_section.title == "Introduction"
        assert intro_section.level == 1

        # Should NOT have a separate root document from 01_intro.adoc
        # There should be no "chapters-01-intro" or similar root section
        all_level_0 = index.get_sections_at_level(0)
        assert len(all_level_0) == 1  # Only "Architecture Documentation"

        # Total sections: arc42 + introduction + goals + architecture-decisions = 4
        assert structure["total_sections"] == 4

    def test_multiple_includes_no_duplicates(self, tmp_path):
        """Test that multiple included files don't appear as root documents."""
        # Create multiple included files
        chapters = tmp_path / "chapters"
        chapters.mkdir()

        for i, title in enumerate(["Introduction", "Setup", "Usage"], start=1):
            chapter_file = chapters / f"0{i}_{title.lower()}.adoc"
            chapter_file.write_text(f"== {title}\n\nContent for {title}.")

        # Main file includes all chapters
        main = tmp_path / "main.adoc"
        main.write_text("""= User Guide

include::chapters/01_introduction.adoc[]

include::chapters/02_setup.adoc[]

include::chapters/03_usage.adoc[]
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        structure = index.get_structure()

        # Should have exactly 1 root document (User Guide)
        assert len(structure["sections"]) == 1
        assert structure["sections"][0]["title"] == "User Guide"

        # Total sections should be reasonable (not inflated by duplicates)
        # 1 root + 3 chapters = 4
        assert structure["total_sections"] == 4

    def test_nested_includes_not_in_structure(self, tmp_path):
        """Test transitive includes (A includes B includes C)."""
        # Create nested structure:
        # main.adoc -> chapter.adoc -> section.adoc
        # Only main.adoc should be root document

        section = tmp_path / "section.adoc"
        section.write_text("=== Detailed Section\n\nDetails here.")

        chapter = tmp_path / "chapter.adoc"
        chapter.write_text("""== Chapter

include::section.adoc[]
""")

        main = tmp_path / "main.adoc"
        main.write_text("""= Main Document

include::chapter.adoc[]
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        structure = index.get_structure()

        # Should have exactly 1 root document
        assert len(structure["sections"]) == 1
        assert structure["sections"][0]["title"] == "Main Document"

        # Should be able to find sections from transitively included files
        # "Chapter" and "Detailed Section" should be accessible
        # Path is prefixed with document name (main:chapter per ADR-008)
        chapter_sec = index.get_section("main:chapter")
        assert chapter_sec is not None
        assert chapter_sec.title == "Chapter"

        # Detailed section should also be accessible
        detail_sec = index.get_section("main:chapter.detailed-section")
        assert detail_sec is not None

        # Total sections: main + chapter + detailed section = 3
        assert structure["total_sections"] == 3

    def test_file_included_by_multiple_parents(self, tmp_path):
        """Test that a file included by multiple parents appears only in those parents."""
        # Create shared content
        common = tmp_path / "common.adoc"
        common.write_text("== Common Content\n\nShared across documents.")

        # Create two root documents that both include common.adoc
        guide1 = tmp_path / "user-guide.adoc"
        guide1.write_text("""= User Guide

include::common.adoc[]

== User Guide Content
""")

        guide2 = tmp_path / "admin-guide.adoc"
        guide2.write_text("""= Admin Guide

include::common.adoc[]

== Admin Guide Content
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        structure = index.get_structure()

        # Should have 2 root documents (not 3)
        assert len(structure["sections"]) == 2
        titles = {s["title"] for s in structure["sections"]}
        assert titles == {"User Guide", "Admin Guide"}

        # Common content should NOT be a separate root document
        # It appears in both parent documents

    def test_source_location_preserved_for_included_content(self, tmp_path):
        """Test that SourceLocation points to actual physical file for included content."""
        # Create included file
        intro = tmp_path / "chapters" / "intro.adoc"
        intro.parent.mkdir()
        intro.write_text("""== Introduction

This content is in chapters/intro.adoc.
""")

        # Main file includes it
        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::chapters/intro.adoc[]
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        # Get the Introduction section (path is prefixed with document name)
        intro_section = index.get_section("main:introduction")
        assert intro_section is not None

        # SourceLocation should point to chapters/intro.adoc, NOT main.adoc
        assert intro_section.source_location.file == intro
        assert "intro.adoc" in str(intro_section.source_location.file)

    def test_search_no_duplicates(self, tmp_path):
        """Test that search results don't contain duplicates from included files."""
        # Create included file with distinctive content
        intro = tmp_path / "intro.adoc"
        intro.write_text("""== Introduction

The special keyword UNIQUE-SEARCH-TERM appears here.
""")

        # Main file includes it
        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::intro.adoc[]

== Other Content

No duplicates here.
""")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        # Search for unique term
        results = index.search("UNIQUE-SEARCH-TERM", max_results=10)

        # Should find exactly ONE result (not two from parsing intro.adoc twice)
        assert len(results) == 1
        assert "UNIQUE-SEARCH-TERM" in results[0].context

    def test_standalone_files_still_parsed(self, tmp_path):
        """Test that files NOT included by anyone are still parsed as root documents."""
        # Create two standalone files (no includes between them)
        guide1 = tmp_path / "guide1.adoc"
        guide1.write_text("= Guide 1\n\nContent 1")

        guide2 = tmp_path / "guide2.adoc"
        guide2.write_text("= Guide 2\n\nContent 2")

        # Build index
        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        structure = index.get_structure()

        # Both should be root documents
        assert len(structure["sections"]) == 2
        titles = {s["title"] for s in structure["sections"]}
        assert titles == {"Guide 1", "Guide 2"}

    def test_update_included_content(self, tmp_path):
        """Test that updates to included content target the correct physical file."""
        # Create included file
        intro = tmp_path / "chapters" / "intro.adoc"
        intro.parent.mkdir()
        intro.write_text("""== Introduction

Original content here.
""")

        # Main file includes it
        main = tmp_path / "main.adoc"
        main.write_text("""= Main

include::chapters/intro.adoc[]
""")

        # Build index
        from dacli.file_handler import FileSystemHandler
        from dacli.services.content_service import update_section

        index = StructureIndex()
        asciidoc_parser = AsciidocStructureParser(tmp_path)
        markdown_parser = MarkdownStructureParser(tmp_path)
        file_handler = FileSystemHandler()

        _build_index(
            tmp_path,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=False,
            include_hidden=False,
        )

        # Update the Introduction section
        result = update_section(
            index,
            file_handler,
            "main:introduction",
            "Updated content from test.",
            preserve_title=True,
        )

        assert result["success"] is True

        # Verify the UPDATE went to the included file, NOT main.adoc
        intro_content = intro.read_text()
        assert "Updated content from test" in intro_content
        assert "Original content" not in intro_content

        # Main file should be unchanged (still has include directive)
        main_content = main.read_text()
        assert "include::chapters/intro.adoc[]" in main_content
        assert "Updated content" not in main_content
