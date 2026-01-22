"""Unit tests for core data models (Issue #2).

Tests cover:
- SourceLocation: Position tracking with include resolution
- Section: Hierarchical document sections
- Element: Extractable content elements (code, tables, images, etc.)
- CrossReference: Internal and external references
- Document: Base class for parsed documents
- JSON serialization for API responses
"""

from pathlib import Path


class TestSourceLocation:
    """Tests for SourceLocation dataclass."""

    def test_create_source_location_basic(self):
        """Test creating a basic SourceLocation with file and line."""
        from dacli.models import SourceLocation

        loc = SourceLocation(file=Path("docs/intro.adoc"), line=42)

        assert loc.file == Path("docs/intro.adoc")
        assert loc.line == 42
        assert loc.resolved_from is None

    def test_create_source_location_with_resolved_from(self):
        """Test SourceLocation with include resolution tracking."""
        from dacli.models import SourceLocation

        loc = SourceLocation(
            file=Path("chapters/intro.adoc"),
            line=10,
            resolved_from=Path("main.adoc"),
        )

        assert loc.file == Path("chapters/intro.adoc")
        assert loc.line == 10
        assert loc.resolved_from == Path("main.adoc")

    def test_source_location_line_is_positive(self):
        """Test that line numbers are 1-based (positive integers)."""
        from dacli.models import SourceLocation

        loc = SourceLocation(file=Path("test.adoc"), line=1)
        assert loc.line >= 1


class TestSection:
    """Tests for Section dataclass."""

    def test_create_section_basic(self):
        """Test creating a basic section."""
        from dacli.models import Section, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=5)
        section = Section(
            title="Introduction",
            level=1,
            path="introduction",
            source_location=loc,
        )

        assert section.title == "Introduction"
        assert section.level == 1
        assert section.path == "introduction"
        assert section.source_location == loc
        assert section.children == []
        assert section.anchor is None

    def test_create_section_with_children(self):
        """Test section with child sections."""
        from dacli.models import Section, SourceLocation

        loc1 = SourceLocation(file=Path("doc.adoc"), line=5)
        loc2 = SourceLocation(file=Path("doc.adoc"), line=15)

        child = Section(
            title="Goals",
            level=2,
            path="introduction.goals",
            source_location=loc2,
        )
        parent = Section(
            title="Introduction",
            level=1,
            path="introduction",
            source_location=loc1,
            children=[child],
        )

        assert len(parent.children) == 1
        assert parent.children[0].title == "Goals"

    def test_create_section_with_anchor(self):
        """Test section with explicit anchor."""
        from dacli.models import Section, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=5)
        section = Section(
            title="Introduction",
            level=1,
            path="introduction",
            source_location=loc,
            anchor="intro-anchor",
        )

        assert section.anchor == "intro-anchor"


class TestElement:
    """Tests for Element dataclass."""

    def test_create_code_element(self):
        """Test creating a code block element."""
        from dacli.models import Element, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=20)
        element = Element(
            type="code",
            source_location=loc,
            attributes={"language": "python", "title": "Example"},
            parent_section="introduction",
        )

        assert element.type == "code"
        assert element.source_location == loc
        assert element.attributes["language"] == "python"
        assert element.parent_section == "introduction"

    def test_create_table_element(self):
        """Test creating a table element."""
        from dacli.models import Element, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=30)
        element = Element(
            type="table",
            source_location=loc,
            attributes={"columns": 3, "rows": 5, "title": "Data Table"},
            parent_section="chapter-1.data",
        )

        assert element.type == "table"
        assert element.attributes["columns"] == 3
        assert element.attributes["rows"] == 5

    def test_create_image_element(self):
        """Test creating an image element."""
        from dacli.models import Element, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=40)
        element = Element(
            type="image",
            source_location=loc,
            attributes={
                "src": "images/diagram.png",
                "alt": "Architecture Diagram",
                "width": 400,
                "height": 300,
            },
            parent_section="architecture",
        )

        assert element.type == "image"
        assert element.attributes["src"] == "images/diagram.png"
        assert element.attributes["alt"] == "Architecture Diagram"

    def test_create_plantuml_element(self):
        """Test creating a PlantUML diagram element."""
        from dacli.models import Element, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=50)
        element = Element(
            type="plantuml",
            source_location=loc,
            attributes={
                "name": "sequence-diagram",
                "format": "svg",
                "content": "@startuml\nAlice -> Bob\n@enduml",
            },
            parent_section="architecture.diagrams",
        )

        assert element.type == "plantuml"
        assert element.attributes["name"] == "sequence-diagram"
        assert element.attributes["format"] == "svg"

    def test_create_admonition_element(self):
        """Test creating an admonition element."""
        from dacli.models import Element, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=60)
        element = Element(
            type="admonition",
            source_location=loc,
            attributes={
                "admonition_type": "WARNING",
                "content": "This is deprecated.",
            },
            parent_section="api.deprecated",
        )

        assert element.type == "admonition"
        assert element.attributes["admonition_type"] == "WARNING"


class TestCrossReference:
    """Tests for CrossReference dataclass."""

    def test_create_internal_reference(self):
        """Test creating an internal cross-reference."""
        from dacli.models import CrossReference, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=25)
        ref = CrossReference(
            type="internal",
            target="section-anchor",
            source_location=loc,
        )

        assert ref.type == "internal"
        assert ref.target == "section-anchor"
        assert ref.text is None
        assert ref.source_location == loc

    def test_create_internal_reference_with_text(self):
        """Test internal reference with custom link text."""
        from dacli.models import CrossReference, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=25)
        ref = CrossReference(
            type="internal",
            target="section-anchor",
            text="See Introduction",
            source_location=loc,
        )

        assert ref.text == "See Introduction"

    def test_create_external_reference(self):
        """Test creating an external cross-reference (xref)."""
        from dacli.models import CrossReference, SourceLocation

        loc = SourceLocation(file=Path("doc.adoc"), line=30)
        ref = CrossReference(
            type="external",
            target="other-file.adoc#anchor",
            text="Related Topic",
            source_location=loc,
        )

        assert ref.type == "external"
        assert ref.target == "other-file.adoc#anchor"
        assert ref.text == "Related Topic"


class TestDocument:
    """Tests for Document base class."""

    def test_create_document_basic(self):
        """Test creating a basic document."""
        from dacli.models import Document

        doc = Document(
            file_path=Path("docs/intro.adoc"),
            title="Introduction",
        )

        assert doc.file_path == Path("docs/intro.adoc")
        assert doc.title == "Introduction"
        assert doc.sections == []
        assert doc.elements == []

    def test_create_document_with_sections(self):
        """Test document with sections."""
        from dacli.models import Document, Section, SourceLocation

        loc = SourceLocation(file=Path("docs/intro.adoc"), line=1)
        section = Section(
            title="Overview",
            level=1,
            path="overview",
            source_location=loc,
        )
        doc = Document(
            file_path=Path("docs/intro.adoc"),
            title="Introduction",
            sections=[section],
        )

        assert len(doc.sections) == 1
        assert doc.sections[0].title == "Overview"

    def test_create_document_with_elements(self):
        """Test document with elements."""
        from dacli.models import Document, Element, SourceLocation

        loc = SourceLocation(file=Path("docs/intro.adoc"), line=10)
        element = Element(
            type="code",
            source_location=loc,
            attributes={"language": "python"},
            parent_section="overview",
        )
        doc = Document(
            file_path=Path("docs/intro.adoc"),
            title="Introduction",
            elements=[element],
        )

        assert len(doc.elements) == 1
        assert doc.elements[0].type == "code"


class TestJSONSerialization:
    """Tests for JSON serialization of data models."""

    def test_source_location_to_dict(self):
        """Test SourceLocation converts to dict for JSON."""
        from dacli.models import SourceLocation, model_to_dict

        loc = SourceLocation(file=Path("doc.adoc"), line=42)
        data = model_to_dict(loc)

        assert isinstance(data, dict)
        assert data["file"] == "doc.adoc"
        assert data["line"] == 42
        assert data["resolved_from"] is None

    def test_source_location_with_resolved_from_to_dict(self):
        """Test SourceLocation with resolved_from converts to dict."""
        from dacli.models import SourceLocation, model_to_dict

        loc = SourceLocation(
            file=Path("chapters/intro.adoc"),
            line=10,
            resolved_from=Path("main.adoc"),
        )
        data = model_to_dict(loc)

        assert data["resolved_from"] == "main.adoc"

    def test_section_to_dict(self):
        """Test Section converts to dict for JSON."""
        from dacli.models import Section, SourceLocation, model_to_dict

        loc = SourceLocation(file=Path("doc.adoc"), line=5)
        section = Section(
            title="Introduction",
            level=1,
            path="introduction",
            source_location=loc,
            anchor="intro",
        )
        data = model_to_dict(section)

        assert data["title"] == "Introduction"
        assert data["level"] == 1
        assert data["path"] == "introduction"
        assert data["anchor"] == "intro"
        assert isinstance(data["source_location"], dict)
        assert data["source_location"]["file"] == "doc.adoc"

    def test_section_with_children_to_dict(self):
        """Test Section with children converts to dict recursively."""
        from dacli.models import Section, SourceLocation, model_to_dict

        loc1 = SourceLocation(file=Path("doc.adoc"), line=5)
        loc2 = SourceLocation(file=Path("doc.adoc"), line=15)
        child = Section(
            title="Goals",
            level=2,
            path="introduction.goals",
            source_location=loc2,
        )
        parent = Section(
            title="Introduction",
            level=1,
            path="introduction",
            source_location=loc1,
            children=[child],
        )
        data = model_to_dict(parent)

        assert len(data["children"]) == 1
        assert data["children"][0]["title"] == "Goals"

    def test_element_to_dict(self):
        """Test Element converts to dict for JSON."""
        from dacli.models import Element, SourceLocation, model_to_dict

        loc = SourceLocation(file=Path("doc.adoc"), line=20)
        element = Element(
            type="code",
            source_location=loc,
            attributes={"language": "python"},
            parent_section="introduction",
        )
        data = model_to_dict(element)

        assert data["type"] == "code"
        assert data["attributes"]["language"] == "python"
        assert data["parent_section"] == "introduction"

    def test_document_to_dict(self):
        """Test Document converts to dict for JSON."""
        from dacli.models import Document, model_to_dict

        doc = Document(
            file_path=Path("docs/intro.adoc"),
            title="Introduction",
        )
        data = model_to_dict(doc)

        assert data["file_path"] == "docs/intro.adoc"
        assert data["title"] == "Introduction"
        assert data["sections"] == []
        assert data["elements"] == []

    def test_cross_reference_to_dict(self):
        """Test CrossReference converts to dict for JSON."""
        from dacli.models import CrossReference, SourceLocation, model_to_dict

        loc = SourceLocation(file=Path("doc.adoc"), line=25)
        ref = CrossReference(
            type="internal",
            target="section-anchor",
            text="See Section",
            source_location=loc,
        )
        data = model_to_dict(ref)

        assert data["type"] == "internal"
        assert data["target"] == "section-anchor"
        assert data["text"] == "See Section"
