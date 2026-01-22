"""Tests for the Structure Index component.

These tests verify the in-memory index that enables fast lookups
of document structure and sections.
"""

from pathlib import Path

from dacli.models import Document, Element, Section, SourceLocation
from dacli.structure_index import StructureIndex


class TestStructureIndexBasic:
    """Basic instantiation and setup tests."""

    def test_index_can_be_instantiated(self):
        """AC-IDX-01: Index can be created."""
        index = StructureIndex()
        assert index is not None

    def test_empty_index_returns_empty_structure(self):
        """Empty index returns empty structure."""
        index = StructureIndex()
        structure = index.get_structure()
        assert structure["sections"] == []
        assert structure["total_sections"] == 0


class TestIndexBuilding:
    """Tests for building index from parser output."""

    def test_build_from_single_document(self):
        """AC-IDX-01: Index is built from single document."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test Document",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    children=[],
                )
            ],
            elements=[],
        )
        index.build_from_documents([doc])

        structure = index.get_structure()
        assert structure["total_sections"] == 1

    def test_build_from_multiple_documents(self):
        """AC-IDX-02: Index is built from multiple documents."""
        index = StructureIndex()
        doc1 = Document(
            file_path=Path("doc1.adoc"),
            title="Document 1",
            sections=[
                Section(
                    title="Section A",
                    level=1,
                    path="section-a",
                    source_location=SourceLocation(file=Path("doc1.adoc"), line=1),
                )
            ],
        )
        doc2 = Document(
            file_path=Path("doc2.md"),
            title="Document 2",
            sections=[
                Section(
                    title="Section B",
                    level=1,
                    path="section-b",
                    source_location=SourceLocation(file=Path("doc2.md"), line=1),
                )
            ],
        )
        index.build_from_documents([doc1, doc2])

        structure = index.get_structure()
        assert structure["total_sections"] == 2

    def test_nested_sections_are_indexed(self):
        """Nested sections are properly indexed."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Section 1.1",
                            level=2,
                            path="chapter-1.section-1-1",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                        )
                    ],
                )
            ],
        )
        index.build_from_documents([doc])

        # Both parent and child should be findable
        assert index.get_section("chapter-1") is not None
        assert index.get_section("chapter-1.section-1-1") is not None

    def test_elements_are_indexed(self):
        """Elements from documents are indexed."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={"language": "python"},
                    parent_section="intro",
                ),
                Element(
                    type="table",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    attributes={"columns": 3},
                    parent_section="data",
                ),
            ],
        )
        index.build_from_documents([doc])

        elements = index.get_elements()
        assert len(elements) == 2


class TestGetStructure:
    """Tests for get_structure() method."""

    def test_get_structure_returns_hierarchical_tree(self):
        """AC-IDX-03: get_structure() returns correct hierarchical tree."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Section 1.1",
                            level=2,
                            path="chapter-1.section-1-1",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                        )
                    ],
                ),
                Section(
                    title="Chapter 2",
                    level=1,
                    path="chapter-2",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )
        index.build_from_documents([doc])

        structure = index.get_structure()
        assert structure["total_sections"] == 3
        assert len(structure["sections"]) == 2
        assert structure["sections"][0]["title"] == "Chapter 1"
        assert len(structure["sections"][0]["children"]) == 1

    def test_get_structure_with_max_depth(self):
        """get_structure() respects max_depth parameter."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Section 1.1",
                            level=2,
                            path="chapter-1.section-1-1",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                            children=[
                                Section(
                                    title="Subsection 1.1.1",
                                    level=3,
                                    path="chapter-1.section-1-1/subsection-1-1-1",
                                    source_location=SourceLocation(
                                        file=Path("test.adoc"), line=15
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        index.build_from_documents([doc])

        # max_depth=1 should only return level 1 sections
        structure = index.get_structure(max_depth=1)
        assert len(structure["sections"]) == 1
        assert structure["sections"][0]["children"] == []

        # max_depth=2 should return level 1 and 2
        structure = index.get_structure(max_depth=2)
        assert len(structure["sections"][0]["children"]) == 1
        assert structure["sections"][0]["children"][0]["children"] == []


class TestGetSection:
    """Tests for get_section() method."""

    def test_get_section_returns_section_by_path(self):
        """AC-IDX-04: get_section(path) returns section with location."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    path="introduction",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                )
            ],
        )
        index.build_from_documents([doc])

        section = index.get_section("introduction")
        assert section is not None
        assert section.title == "Introduction"
        assert section.source_location.line == 5

    def test_get_section_returns_none_for_invalid_path(self):
        """get_section() returns None for non-existent path."""
        index = StructureIndex()
        index.build_from_documents([])

        section = index.get_section("nonexistent")
        assert section is None

    def test_get_section_finds_nested_sections(self):
        """get_section() finds deeply nested sections."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter",
                    level=1,
                    path="chapter",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Section",
                            level=2,
                            path="chapter.section",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                            children=[
                                Section(
                                    title="Subsection",
                                    level=3,
                                    path="chapter.section/subsection",
                                    source_location=SourceLocation(
                                        file=Path("test.adoc"), line=20
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        index.build_from_documents([doc])

        section = index.get_section("chapter.section/subsection")
        assert section is not None
        assert section.title == "Subsection"


class TestGetSectionsAtLevel:
    """Tests for get_sections_at_level() method."""

    def test_get_sections_at_level_returns_correct_sections(self):
        """get_sections_at_level() returns all sections at specified level."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Section 1.1",
                            level=2,
                            path="chapter-1.section-1-1",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=5
                            ),
                        )
                    ],
                ),
                Section(
                    title="Chapter 2",
                    level=1,
                    path="chapter-2",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    children=[
                        Section(
                            title="Section 2.1",
                            level=2,
                            path="chapter-2.section-2-1",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=25
                            ),
                        )
                    ],
                ),
            ],
        )
        index.build_from_documents([doc])

        level_1 = index.get_sections_at_level(1)
        assert len(level_1) == 2
        assert all(s.level == 1 for s in level_1)

        level_2 = index.get_sections_at_level(2)
        assert len(level_2) == 2
        assert all(s.level == 2 for s in level_2)

    def test_get_sections_at_level_returns_empty_for_no_match(self):
        """get_sections_at_level() returns empty list when no match."""
        index = StructureIndex()
        index.build_from_documents([])

        sections = index.get_sections_at_level(5)
        assert sections == []


class TestGetElements:
    """Tests for get_elements() method."""

    def test_get_elements_returns_all_elements(self):
        """get_elements() returns all elements when no filter."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={"language": "python"},
                    parent_section="intro",
                ),
                Element(
                    type="table",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    attributes={"columns": 3},
                    parent_section="data",
                ),
            ],
        )
        index.build_from_documents([doc])

        elements = index.get_elements()
        assert len(elements) == 2

    def test_get_elements_filters_by_type(self):
        """AC-IDX-05: get_elements(type) filters correctly."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={"language": "python"},
                    parent_section="intro",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=15),
                    attributes={"language": "java"},
                    parent_section="intro",
                ),
                Element(
                    type="table",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    attributes={"columns": 3},
                    parent_section="data",
                ),
            ],
        )
        index.build_from_documents([doc])

        code_elements = index.get_elements(element_type="code")
        assert len(code_elements) == 2
        assert all(e.type == "code" for e in code_elements)

        table_elements = index.get_elements(element_type="table")
        assert len(table_elements) == 1

    def test_get_elements_filters_by_section(self):
        """get_elements() filters by section path."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={"language": "python"},
                    parent_section="intro",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=15),
                    attributes={"language": "java"},
                    parent_section="chapter-1",
                ),
            ],
        )
        index.build_from_documents([doc])

        intro_elements = index.get_elements(section_path="intro")
        assert len(intro_elements) == 1
        assert intro_elements[0].attributes["language"] == "python"

    def test_get_elements_filters_by_type_and_section(self):
        """get_elements() combines type and section filters."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={},
                    parent_section="intro",
                ),
                Element(
                    type="table",
                    source_location=SourceLocation(file=Path("test.adoc"), line=10),
                    attributes={},
                    parent_section="intro",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    attributes={},
                    parent_section="chapter-1",
                ),
            ],
        )
        index.build_from_documents([doc])

        elements = index.get_elements(element_type="code", section_path="intro")
        assert len(elements) == 1


class TestSearch:
    """Tests for search() method."""

    def test_search_finds_matching_sections(self):
        """AC-IDX-06: search(query) finds matching sections."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test Document",
            sections=[
                Section(
                    title="Introduction to Python",
                    level=1,
                    path="introduction",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                ),
                Section(
                    title="Java Basics",
                    level=1,
                    path="java-basics",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )
        index.build_from_documents([doc])

        results = index.search("Python")
        assert len(results) == 1
        assert results[0].path == "introduction"

    def test_search_is_case_insensitive_by_default(self):
        """search() is case-insensitive by default."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Python Tutorial",
                    level=1,
                    path="python",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                )
            ],
        )
        index.build_from_documents([doc])

        results = index.search("python")
        assert len(results) == 1

        results = index.search("PYTHON")
        assert len(results) == 1

    def test_search_case_sensitive(self):
        """search() respects case_sensitive flag."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Python Tutorial",
                    level=1,
                    path="python",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                )
            ],
        )
        index.build_from_documents([doc])

        results = index.search("python", case_sensitive=True)
        assert len(results) == 0

        results = index.search("Python", case_sensitive=True)
        assert len(results) == 1

    def test_search_respects_max_results(self):
        """search() respects max_results parameter."""
        index = StructureIndex()
        sections = [
            Section(
                title=f"Section {i}",
                level=1,
                path=f"section-{i}",
                source_location=SourceLocation(file=Path("test.adoc"), line=i * 10),
            )
            for i in range(10)
        ]
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=sections,
        )
        index.build_from_documents([doc])

        results = index.search("Section", max_results=3)
        assert len(results) == 3

    def test_search_with_scope(self):
        """search() respects scope parameter."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Python Section",
                            level=2,
                            path="chapter-1.python",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=5
                            ),
                        )
                    ],
                ),
                Section(
                    title="Chapter 2",
                    level=1,
                    path="chapter-2",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    children=[
                        Section(
                            title="Python Advanced",
                            level=2,
                            path="chapter-2.python",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=25
                            ),
                        )
                    ],
                ),
            ],
        )
        index.build_from_documents([doc])

        # Search within chapter-1 scope
        results = index.search("Python", scope="chapter-1")
        assert len(results) == 1
        assert results[0].path == "chapter-1.python"


class TestDuplicateDetection:
    """Tests for duplicate path detection."""

    def test_duplicate_paths_are_detected(self):
        """AC-IDX-07: Duplicate paths are detected and reported."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Section A",
                    level=1,
                    path="section",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                ),
                Section(
                    title="Section B",
                    level=1,
                    path="section",  # Duplicate path!
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )

        # Build should report duplicates
        warnings = index.build_from_documents([doc])
        assert len(warnings) > 0
        assert any("duplicate" in w.lower() for w in warnings)

    def test_duplicate_paths_rejected_consistently(self):
        """Duplicates are rejected from both path and level indexes."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Section A",
                    level=1,
                    path="section",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                ),
                Section(
                    title="Section B",
                    level=1,
                    path="section",  # Duplicate path!
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )

        # Build should report duplicates
        warnings = index.build_from_documents([doc])
        assert len(warnings) == 1

        # Only first section should be indexed
        section = index.get_section("section")
        assert section is not None
        assert section.title == "Section A"
        assert section.source_location.line == 1

        # Level index should only contain the first section
        level_1_sections = index.get_sections_at_level(1)
        assert len(level_1_sections) == 1
        assert level_1_sections[0].title == "Section A"


class TestGetSectionsByFile:
    """Tests for get_sections_by_file() method."""

    def test_get_sections_by_file_returns_sections_in_file(self):
        """get_sections_by_file() returns all sections defined in a specific file."""
        index = StructureIndex()
        file1 = Path("doc1.adoc")
        file2 = Path("doc2.adoc")
        doc1 = Document(
            file_path=file1,
            title="Document 1",
            sections=[
                Section(
                    title="Chapter A",
                    level=1,
                    path="chapter-a",
                    source_location=SourceLocation(file=file1, line=1),
                ),
                Section(
                    title="Chapter B",
                    level=1,
                    path="chapter-b",
                    source_location=SourceLocation(file=file1, line=20),
                ),
            ],
        )
        doc2 = Document(
            file_path=file2,
            title="Document 2",
            sections=[
                Section(
                    title="Chapter C",
                    level=1,
                    path="chapter-c",
                    source_location=SourceLocation(file=file2, line=1),
                )
            ],
        )
        index.build_from_documents([doc1, doc2])

        # Get sections from file1
        sections = index.get_sections_by_file(file1)
        assert len(sections) == 2
        assert all(s.source_location.file == file1 for s in sections)
        titles = [s.title for s in sections]
        assert "Chapter A" in titles
        assert "Chapter B" in titles

        # Get sections from file2
        sections = index.get_sections_by_file(file2)
        assert len(sections) == 1
        assert sections[0].title == "Chapter C"

    def test_get_sections_by_file_includes_nested_sections(self):
        """get_sections_by_file() includes nested sections in the same file."""
        index = StructureIndex()
        file_path = Path("test.adoc")
        doc = Document(
            file_path=file_path,
            title="Test",
            sections=[
                Section(
                    title="Chapter 1",
                    level=1,
                    path="chapter-1",
                    source_location=SourceLocation(file=file_path, line=1),
                    children=[
                        Section(
                            title="Section 1.1",
                            level=2,
                            path="chapter-1.section-1-1",
                            source_location=SourceLocation(file=file_path, line=10),
                        )
                    ],
                )
            ],
        )
        index.build_from_documents([doc])

        sections = index.get_sections_by_file(file_path)
        assert len(sections) == 2
        titles = [s.title for s in sections]
        assert "Chapter 1" in titles
        assert "Section 1.1" in titles

    def test_get_sections_by_file_returns_empty_for_unknown_file(self):
        """get_sections_by_file() returns empty list for files not in index."""
        index = StructureIndex()
        index.build_from_documents([])

        sections = index.get_sections_by_file(Path("unknown.adoc"))
        assert sections == []

    def test_get_sections_by_file_after_clear(self):
        """get_sections_by_file() returns empty after clear()."""
        index = StructureIndex()
        file_path = Path("test.adoc")
        doc = Document(
            file_path=file_path,
            title="Test",
            sections=[
                Section(
                    title="Chapter",
                    level=1,
                    path="chapter",
                    source_location=SourceLocation(file=file_path, line=1),
                )
            ],
        )
        index.build_from_documents([doc])
        assert len(index.get_sections_by_file(file_path)) == 1

        index.clear()
        assert index.get_sections_by_file(file_path) == []


class TestElementIndex:
    """Tests for element index tracking within sections."""

    def test_elements_have_index_within_section(self):
        """Elements have 0-based index within their parent section."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={"language": "python"},
                    parent_section="intro",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=15),
                    attributes={"language": "java"},
                    parent_section="intro",
                ),
                Element(
                    type="table",
                    source_location=SourceLocation(file=Path("test.adoc"), line=25),
                    attributes={},
                    parent_section="intro",
                ),
            ],
        )
        index.build_from_documents([doc])

        intro_elements = index.get_elements(section_path="intro")
        assert len(intro_elements) == 3

        # Elements should have index field
        for i, elem in enumerate(intro_elements):
            assert hasattr(elem, "index"), "Element should have index attribute"
            assert elem.index == i

    def test_element_index_is_per_section(self):
        """Element index resets for each section."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={},
                    parent_section="section-a",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=10),
                    attributes={},
                    parent_section="section-a",
                ),
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                    attributes={},
                    parent_section="section-b",
                ),
            ],
        )
        index.build_from_documents([doc])

        section_a_elements = index.get_elements(section_path="section-a")
        assert section_a_elements[0].index == 0
        assert section_a_elements[1].index == 1

        section_b_elements = index.get_elements(section_path="section-b")
        assert section_b_elements[0].index == 0  # Index resets for new section

    def test_element_index_in_stats(self):
        """Stats should include element counts with index info."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={},
                    parent_section="intro",
                ),
            ],
        )
        index.build_from_documents([doc])

        stats = index.stats()
        assert stats["total_elements"] == 1


class TestClearAndStats:
    """Tests for clear() and stats() methods."""

    def test_clear_removes_all_data(self):
        """clear() removes all indexed data."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter",
                    level=1,
                    path="chapter",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                )
            ],
        )
        index.build_from_documents([doc])
        assert index.get_structure()["total_sections"] == 1

        index.clear()
        assert index.get_structure()["total_sections"] == 0

    def test_stats_returns_index_statistics(self):
        """stats() returns accurate index statistics."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Chapter",
                    level=1,
                    path="chapter",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                )
            ],
            elements=[
                Element(
                    type="code",
                    source_location=SourceLocation(file=Path("test.adoc"), line=5),
                    attributes={},
                    parent_section="chapter",
                )
            ],
        )
        index.build_from_documents([doc])

        stats = index.stats()
        assert stats["total_sections"] == 1
        assert stats["total_elements"] == 1
        assert stats["total_documents"] == 1
        assert stats["index_ready"] is True


class TestContentSearch:
    """Tests for full-text search in section content (not just titles).

    These tests verify AC-SEARCH-CONTENT: Search should find matches in
    section body text, not just section titles.
    """

    def test_search_finds_content_in_section_body(self, tmp_path: Path):
        """Search finds text that appears in section body but not in title."""
        # Create a test file with specific content
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document Title

== Introduction

This section contains information about atomic write operations.
The implementation uses backup-and-replace strategy.

== Constraints

This section has different content about performance requirements.
""",
            encoding="utf-8",
        )

        index = StructureIndex()
        doc = Document(
            file_path=test_file,
            title="Document Title",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    path="introduction",
                    source_location=SourceLocation(
                        file=test_file, line=3, end_line=7
                    ),
                ),
                Section(
                    title="Constraints",
                    level=1,
                    path="constraints",
                    source_location=SourceLocation(
                        file=test_file, line=9, end_line=11
                    ),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Search for "atomic" - appears in body of Introduction, not in title
        results = index.search("atomic")
        assert len(results) >= 1
        # Should find the Introduction section
        paths = [r.path for r in results]
        assert "introduction" in paths

    def test_search_returns_context_with_match(self, tmp_path: Path):
        """Search results include context snippet containing the match."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document Title

== Implementation

The system implements atomic writes using a backup-and-replace strategy.
""",
            encoding="utf-8",
        )

        index = StructureIndex()
        doc = Document(
            file_path=test_file,
            title="Document Title",
            sections=[
                Section(
                    title="Implementation",
                    level=1,
                    path="implementation",
                    source_location=SourceLocation(
                        file=test_file, line=3, end_line=5
                    ),
                ),
            ],
        )
        index.build_from_documents([doc])

        results = index.search("atomic")
        assert len(results) >= 1
        # Context should contain the matched word
        assert "atomic" in results[0].context.lower()

    def test_content_search_respects_case_sensitive_flag(self, tmp_path: Path):
        """Case-sensitive search works correctly for content."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document Title

== Section

This contains Performance metrics and optimization details.
""",
            encoding="utf-8",
        )

        index = StructureIndex()
        doc = Document(
            file_path=test_file,
            title="Document Title",
            sections=[
                Section(
                    title="Section",
                    level=1,
                    path="section",
                    source_location=SourceLocation(
                        file=test_file, line=3, end_line=5
                    ),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Case-insensitive should find "Performance" when searching "performance"
        results = index.search("performance", case_sensitive=False)
        assert len(results) >= 1

        # Case-sensitive with lowercase should NOT find "Performance" (capital P)
        results = index.search("performance", case_sensitive=True)
        assert len(results) == 0

    def test_content_search_with_scope_restriction(self, tmp_path: Path):
        """Content search respects scope parameter."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document Title

== Architecture

The architecture uses atomic patterns.

=== Components

These are the components.

== Runtime

The runtime also uses atomic operations.
""",
            encoding="utf-8",
        )

        index = StructureIndex()
        doc = Document(
            file_path=test_file,
            title="Document Title",
            sections=[
                Section(
                    title="Architecture",
                    level=1,
                    path="architecture",
                    source_location=SourceLocation(
                        file=test_file, line=3, end_line=5
                    ),
                    children=[
                        Section(
                            title="Components",
                            level=2,
                            path="architecture.components",
                            source_location=SourceLocation(
                                file=test_file, line=7, end_line=9
                            ),
                        )
                    ],
                ),
                Section(
                    title="Runtime",
                    level=1,
                    path="runtime",
                    source_location=SourceLocation(
                        file=test_file, line=11, end_line=13
                    ),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Search for "atomic" but only in architecture scope
        results = index.search("atomic", scope="architecture")
        paths = [r.path for r in results]
        # Should find architecture but not runtime
        assert "architecture" in paths
        assert "runtime" not in paths


class TestGetSuggestions:
    """Tests for get_suggestions() method.

    This method provides path suggestions when a requested path is not found,
    useful for 404 error responses.
    """

    def test_get_suggestions_returns_similar_paths(self):
        """get_suggestions returns paths similar to the requested path."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    path="introduction",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Goals",
                            level=2,
                            path="introduction.goals",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=5
                            ),
                        ),
                        Section(
                            title="Quality Goals",
                            level=2,
                            path="introduction.quality-goals",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                        ),
                        Section(
                            title="Stakeholders",
                            level=2,
                            path="introduction.stakeholders",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=15
                            ),
                        ),
                    ],
                ),
            ],
        )
        index.build_from_documents([doc])

        # Request non-existent path "introduction.goal" (missing 's')
        suggestions = index.get_suggestions("introduction.goal")
        assert len(suggestions) > 0
        # Should suggest "introduction.goals" as it's very similar
        assert "introduction.goals" in suggestions

    def test_get_suggestions_prefix_match(self):
        """get_suggestions finds paths with matching prefix."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Architecture",
                    level=1,
                    path="architecture",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                    children=[
                        Section(
                            title="Building Blocks",
                            level=2,
                            path="architecture.building-blocks",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=5
                            ),
                        ),
                        Section(
                            title="Runtime View",
                            level=2,
                            path="architecture.runtime",
                            source_location=SourceLocation(
                                file=Path("test.adoc"), line=10
                            ),
                        ),
                    ],
                ),
                Section(
                    title="Quality",
                    level=1,
                    path="quality",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Request non-existent "architecture.overview"
        suggestions = index.get_suggestions("architecture.overview")
        # Should suggest other architecture.* paths
        assert any(s.startswith("architecture.") for s in suggestions)
        # Should NOT suggest unrelated paths like "quality"
        assert "quality" not in suggestions

    def test_get_suggestions_suffix_match(self):
        """get_suggestions finds paths with matching last segment."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Introduction Goals",
                    level=1,
                    path="introduction.goals",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                ),
                Section(
                    title="Quality Goals",
                    level=1,
                    path="quality.goals",
                    source_location=SourceLocation(file=Path("test.adoc"), line=10),
                ),
                Section(
                    title="Architecture",
                    level=1,
                    path="architecture",
                    source_location=SourceLocation(file=Path("test.adoc"), line=20),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Request non-existent "project.goals"
        suggestions = index.get_suggestions("project.goals")
        # Should suggest paths ending with ".goals"
        assert any(s.endswith(".goals") for s in suggestions)

    def test_get_suggestions_limits_results(self):
        """get_suggestions returns at most max_suggestions results."""
        index = StructureIndex()
        # Create many similar sections
        sections = []
        for i in range(10):
            sections.append(
                Section(
                    title=f"Section {i}",
                    level=1,
                    path=f"chapter.section-{i}",
                    source_location=SourceLocation(file=Path("test.adoc"), line=i * 5),
                )
            )
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=sections,
        )
        index.build_from_documents([doc])

        # Request non-existent path with same prefix
        suggestions = index.get_suggestions("chapter.section-unknown", max_suggestions=3)
        assert len(suggestions) <= 3

    def test_get_suggestions_returns_empty_for_no_matches(self):
        """get_suggestions returns empty list when no similar paths exist."""
        index = StructureIndex()
        doc = Document(
            file_path=Path("test.adoc"),
            title="Test",
            sections=[
                Section(
                    title="Architecture",
                    level=1,
                    path="architecture",
                    source_location=SourceLocation(file=Path("test.adoc"), line=1),
                ),
            ],
        )
        index.build_from_documents([doc])

        # Request completely unrelated path
        suggestions = index.get_suggestions("xyz.completely.different.path")
        assert len(suggestions) == 0
