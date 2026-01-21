"""Unit tests for AsciiDoc Parser (Issue #3).

Tests cover:
- Parser instantiation
- Section extraction from AsciiDoc files
- Hierarchical section structure
- Section path generation

AC-ADOC-01: Sektion-Extraktion
"""

from pathlib import Path

import pytest

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "asciidoc"


class TestAsciidocParserBasic:
    """Basic tests for AsciidocParser instantiation."""

    def test_parser_can_be_instantiated(self):
        """Test that AsciidocParser can be instantiated with a base path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."))
        assert parser is not None
        assert parser.base_path == Path(".")

    def test_parser_accepts_max_include_depth(self):
        """Test that parser accepts max_include_depth parameter."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."), max_include_depth=10)
        assert parser.max_include_depth == 10

    def test_parser_default_max_include_depth_is_20(self):
        """Test that default max_include_depth is 20."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=Path("."))
        assert parser.max_include_depth == 20


class TestSectionExtraction:
    """Tests for section extraction (AC-ADOC-01)."""

    def test_parse_file_returns_asciidoc_document(self):
        """Test that parse_file returns an AsciidocDocument."""
        from mcp_server.asciidoc_parser import AsciidocDocument, AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        assert isinstance(doc, AsciidocDocument)

    def test_parse_file_extracts_document_title(self):
        """Test that document title is extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        assert doc.title == "Haupttitel"

    def test_parse_file_extracts_sections(self):
        """Test that sections are extracted from the document."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Document should have a root section (title) with children
        assert len(doc.sections) >= 1

    def test_section_levels_are_correct(self):
        """Test that section levels are correctly determined."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Root section (= Haupttitel) should be level 0
        root = doc.sections[0]
        assert root.level == 0
        assert root.title == "Haupttitel"

        # Children (== Kapitel 1, == Kapitel 2) should be level 1
        assert len(root.children) == 2
        assert root.children[0].level == 1
        assert root.children[0].title == "Kapitel 1"
        assert root.children[1].level == 1
        assert root.children[1].title == "Kapitel 2"

    def test_nested_sections_hierarchy(self):
        """Test that nested sections form correct hierarchy."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        # Kapitel 2 should have Unterkapitel as child
        root = doc.sections[0]
        kapitel2 = root.children[1]
        assert len(kapitel2.children) == 1
        assert kapitel2.children[0].title == "Unterkapitel"
        assert kapitel2.children[0].level == 2


class TestSectionPaths:
    """Tests for hierarchical section paths."""

    def test_root_section_path(self):
        """Test that root section has correct path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.path == "haupttitel"

    def test_chapter_section_path(self):
        """Test that chapter sections have correct hierarchical paths."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.children[0].path == "haupttitel.kapitel-1"
        assert root.children[1].path == "haupttitel.kapitel-2"

    def test_subsection_path(self):
        """Test that subsections have correct hierarchical paths."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        unterkapitel = root.children[1].children[0]
        assert unterkapitel.path == "haupttitel.kapitel-2.unterkapitel"


class TestSourceLocation:
    """Tests for source location tracking."""

    def test_section_has_source_location(self):
        """Test that sections have source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.source_location is not None
        assert root.source_location.file == FIXTURES_DIR / "simple_sections.adoc"
        assert root.source_location.line == 1  # First line

    def test_chapter_source_location(self):
        """Test that chapter has correct source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        kapitel1 = root.children[0]
        assert kapitel1.source_location.line == 3  # "== Kapitel 1" is on line 3

    def test_section_has_end_line(self):
        """Test that sections have end_line calculated."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        assert root.source_location.end_line is not None

    def test_section_end_line_is_before_next_section(self):
        """Test that section end_line is correctly calculated."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        root = doc.sections[0]
        kapitel1 = root.children[0]
        kapitel2 = root.children[1]

        # Kapitel 1 ends just before Kapitel 2 starts
        assert kapitel1.source_location.end_line == kapitel2.source_location.line - 1


class TestDocumentAttributes:
    """Tests for document attribute parsing (AC-ADOC-02)."""

    def test_parse_attributes_from_document(self):
        """Test that document attributes are extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        assert "author" in doc.attributes
        assert doc.attributes["author"] == "Max Mustermann"

    def test_parse_multiple_attributes(self):
        """Test that multiple attributes are extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        assert doc.attributes["author"] == "Max Mustermann"
        assert doc.attributes["project"] == "MCP Server"
        assert doc.attributes["version"] == "1.0.0"
        assert doc.attributes["imagesdir"] == "./images"

    def test_attribute_in_title_is_resolved(self):
        """Test that attribute references in title are resolved."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_attributes.adoc")

        # Title should have {project} resolved to "MCP Server"
        assert doc.title == "MCP Server Dokumentation"


class TestIncludeDirectives:
    """Tests for include directive handling (AC-ADOC-03, AC-ADOC-04)."""

    def test_include_directive_is_recorded(self):
        """Test that include directives are recorded in includes list."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        assert len(doc.includes) == 1
        assert doc.includes[0].target_path == FIXTURES_DIR / "include_partial.adoc"

    def test_include_directive_source_location(self):
        """Test that include directive has correct source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        assert doc.includes[0].source_location.line == 7
        assert doc.includes[0].source_location.file == FIXTURES_DIR / "with_include.adoc"

    def test_included_sections_are_merged(self):
        """Test that sections from included file are merged into document."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        # Document should have root section with 4 children:
        # Erstes Kapitel, Eingebundener Abschnitt (from include), Letztes Kapitel
        root = doc.sections[0]
        section_titles = [s.title for s in root.children]

        assert "Erstes Kapitel" in section_titles
        assert "Eingebundener Abschnitt" in section_titles
        assert "Letztes Kapitel" in section_titles

    def test_included_section_has_resolved_from_info(self):
        """Test that included sections track their source file."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_include.adoc")

        root = doc.sections[0]
        # Find the included section
        included_section = next(
            s for s in root.children if s.title == "Eingebundener Abschnitt"
        )

        # Source location should reference the included file
        assert (
            included_section.source_location.file
            == FIXTURES_DIR / "include_partial.adoc"
        )
        assert included_section.source_location.resolved_from is not None
        assert (
            included_section.source_location.resolved_from.file
            == FIXTURES_DIR / "with_include.adoc"
        )


class TestElementExtraction:
    """Tests for element extraction (AC-ADOC-05, AC-ADOC-06, AC-ADOC-07)."""

    def test_code_block_is_extracted(self):
        """Test that code blocks are extracted as elements."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        code_elements = [e for e in doc.elements if e.type == "code"]
        assert len(code_elements) == 1
        assert code_elements[0].attributes.get("language") == "python"

    def test_code_block_source_location(self):
        """Test that code block has correct source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        code_elements = [e for e in doc.elements if e.type == "code"]
        assert code_elements[0].source_location.line == 8  # Line of ----

    def test_code_block_parent_section(self):
        """Test that code block has correct parent section."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        code_elements = [e for e in doc.elements if e.type == "code"]
        assert "code-beispiele" in code_elements[0].parent_section

    def test_table_is_extracted(self):
        """Test that tables are extracted as elements."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        table_elements = [e for e in doc.elements if e.type == "table"]
        assert len(table_elements) == 1

    def test_image_is_extracted(self):
        """Test that images are extracted as elements."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        image_elements = [e for e in doc.elements if e.type == "image"]
        assert len(image_elements) == 1
        assert image_elements[0].attributes.get("target") == "diagram.png"

    def test_admonition_is_extracted(self):
        """Test that admonitions are extracted as elements."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        admonition_elements = [e for e in doc.elements if e.type == "admonition"]
        assert len(admonition_elements) == 2  # NOTE and WARNING

    def test_plantuml_block_is_extracted(self):
        """Test that PlantUML blocks are extracted as elements (AC-ADOC-06)."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        plantuml_elements = [e for e in doc.elements if e.type == "plantuml"]
        assert len(plantuml_elements) == 1

    def test_plantuml_block_has_attributes(self):
        """Test that PlantUML block has name and format attributes."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        plantuml_elements = [e for e in doc.elements if e.type == "plantuml"]
        assert plantuml_elements[0].attributes.get("name") == "sequenz-diagramm"
        assert plantuml_elements[0].attributes.get("format") == "svg"

    def test_plantuml_block_without_optional_attributes(self):
        """Test that PlantUML block without name/format does not have None values."""
        import tempfile
        from pathlib import Path

        from mcp_server.asciidoc_parser import AsciidocParser

        # Create a temporary test file with PlantUML block without attributes
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".adoc", delete=False, dir=FIXTURES_DIR
        ) as f:
            f.write(
                """= Test Document

[plantuml]
----
@startuml
Alice -> Bob: Test
@enduml
----
"""
            )
            temp_file = Path(f.name)

        try:
            parser = AsciidocParser(base_path=FIXTURES_DIR)
            doc = parser.parse_file(temp_file)

            plantuml_elements = [e for e in doc.elements if e.type == "plantuml"]
            assert len(plantuml_elements) == 1

            # Ensure no None values in attributes
            attrs = plantuml_elements[0].attributes
            assert None not in attrs.values()
            # The attributes dict should be empty if no name/format were provided
            assert "name" not in attrs or attrs["name"] is not None
            assert "format" not in attrs or attrs["format"] is not None
        finally:
            # Clean up temp file
            temp_file.unlink()


class TestCrossReferences:
    """Tests for cross-reference extraction (AC-ADOC-08)."""

    def test_cross_reference_is_extracted(self):
        """Test that cross-references are extracted."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_xrefs.adoc")

        assert len(doc.cross_references) >= 1

    def test_cross_reference_target(self):
        """Test that cross-reference target is captured."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_xrefs.adoc")

        targets = [xref.target for xref in doc.cross_references]
        assert "details" in targets
        assert "intro" in targets

    def test_cross_reference_with_text(self):
        """Test that cross-reference display text is captured."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_xrefs.adoc")

        # Find xref with custom text
        xref_with_text = next(
            (x for x in doc.cross_references if x.text), None
        )
        assert xref_with_text is not None
        assert xref_with_text.text in ["Einleitung", "den Details"]

    def test_cross_reference_source_location(self):
        """Test that cross-reference has source location."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_xrefs.adoc")

        assert doc.cross_references[0].source_location is not None
        assert doc.cross_references[0].source_location.file == FIXTURES_DIR / "with_xrefs.adoc"


class TestInterfaceMethods:
    """Tests for interface methods get_section() and get_elements()."""

    def test_get_section_returns_section_by_path(self):
        """Test that get_section returns correct section by path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        section = parser.get_section(doc, "haupttitel.kapitel-1")
        assert section is not None
        assert section.title == "Kapitel 1"

    def test_get_section_returns_none_for_invalid_path(self):
        """Test that get_section returns None for non-existent path."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        section = parser.get_section(doc, "non.existent.path")
        assert section is None

    def test_get_section_returns_nested_section(self):
        """Test that get_section returns deeply nested section."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        section = parser.get_section(doc, "haupttitel.kapitel-2.unterkapitel")
        assert section is not None
        assert section.title == "Unterkapitel"

    def test_get_elements_returns_all_elements(self):
        """Test that get_elements returns all elements."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        elements = parser.get_elements(doc)
        assert len(elements) >= 4  # code, table, image, admonitions

    def test_get_elements_filters_by_type(self):
        """Test that get_elements filters by element type."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "with_elements.adoc")

        code_elements = parser.get_elements(doc, element_type="code")
        assert len(code_elements) == 1
        assert all(e.type == "code" for e in code_elements)

    def test_get_elements_returns_empty_for_no_match(self):
        """Test that get_elements returns empty list for non-existent type."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        doc = parser.parse_file(FIXTURES_DIR / "simple_sections.adoc")

        elements = parser.get_elements(doc, element_type="plantuml")
        assert elements == []


class TestCircularIncludeDetection:
    """Tests for circular include detection (AC-ADOC-04)."""

    def test_circular_include_raises_error(self):
        """Test that circular includes raise CircularIncludeError."""
        from mcp_server.asciidoc_parser import AsciidocParser, CircularIncludeError

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        with pytest.raises(CircularIncludeError):
            parser.parse_file(FIXTURES_DIR / "circular_a.adoc")

    def test_circular_include_error_contains_path_info(self):
        """Test that CircularIncludeError contains information about the cycle."""
        from mcp_server.asciidoc_parser import AsciidocParser, CircularIncludeError

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        try:
            parser.parse_file(FIXTURES_DIR / "circular_a.adoc")
            assert False, "Expected CircularIncludeError"
        except CircularIncludeError as e:
            # Error message should contain file path
            assert "circular" in str(e).lower()


class TestEdgeCases:
    """Tests for edge cases."""

    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises FileNotFoundError."""
        from mcp_server.asciidoc_parser import AsciidocParser

        parser = AsciidocParser(base_path=FIXTURES_DIR)
        with pytest.raises(FileNotFoundError):
            parser.parse_file(FIXTURES_DIR / "nonexistent.adoc")

    def test_parse_empty_file(self):
        """Test that parsing empty file returns document with no sections."""
        from mcp_server.asciidoc_parser import AsciidocParser

        # Create empty file
        empty_file = FIXTURES_DIR / "empty.adoc"
        empty_file.write_text("")

        try:
            parser = AsciidocParser(base_path=FIXTURES_DIR)
            doc = parser.parse_file(empty_file)
            assert doc.title == ""
            assert doc.sections == []
        finally:
            empty_file.unlink()
