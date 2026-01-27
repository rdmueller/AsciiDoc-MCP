"""Tests for Issue #208: Insert changes section hierarchy unexpectedly.

These tests verify that inserting content "after" a section with children
inserts AFTER all descendants, not between the parent and its children.
"""

from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.structure_index import StructureIndex


class TestInsertAfterWithChildren:
    """Test that insert 'after' preserves parent-child relationships."""

    @pytest.fixture
    def test_file(self, tmp_path: Path) -> Path:
        """Create test file with nested structure."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

=== Subsection A1

Child of A

== Section B

Content B
""",
            encoding="utf-8",
        )
        return test_file

    @pytest.fixture
    def index(self, tmp_path: Path, test_file: Path) -> StructureIndex:
        """Create structure index from test file."""
        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])
        return index

    def test_insert_after_parent_preserves_child(self, tmp_path: Path, index: StructureIndex):
        """Insert after parent should not steal its children (Issue #208)."""
        # Get initial structure
        section_a = index.get_section("test:section-a")
        assert section_a is not None
        assert len(section_a.children) == 1
        assert section_a.children[0].title == "Subsection A1"

        # Insert after Section A
        from dacli.api.manipulation import _file_handler, _get_section_end_with_children

        test_file = tmp_path / "test.adoc"

        # Get end line including children
        end_with_children = _get_section_end_with_children(section_a, test_file)

        # Read file and insert
        content = _file_handler.read_file(test_file)
        lines = content.splitlines(keepends=True)

        new_content = "\n== Section A.5\n\nInserted section\n"

        new_lines = (
            lines[:end_with_children]
            + [new_content]
            + lines[end_with_children:]
        )

        new_file_content = "".join(new_lines)
        _file_handler.write_file(test_file, new_file_content)

        # Re-parse and check structure
        parser = AsciidocStructureParser(base_path=tmp_path)
        doc = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc])

        # Verify Section A still has its child
        section_a_new = index_new.get_section("test:section-a")
        assert section_a_new is not None
        assert len(section_a_new.children) == 1
        assert section_a_new.children[0].title == "Subsection A1"

        # Verify new section exists as a sibling (not parent of A1)
        section_a5 = index_new.get_section("test:section-a5")
        assert section_a5 is not None
        assert len(section_a5.children) == 0  # No children stolen!

    def test_insert_after_deeply_nested(self, tmp_path: Path):
        """Insert after section with deeply nested children (3+ levels)."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

=== Level 2 Child

Content

==== Level 3 Child

Deep content

===== Level 4 Child

Very deep

== Section B
""",
            encoding="utf-8",
        )

        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])

        section_a = index.get_section("test:section-a")
        assert section_a is not None

        from dacli.api.manipulation import _file_handler, _get_section_end_with_children

        # Insert after Section A (which has deeply nested children)
        end_with_children = _get_section_end_with_children(section_a, test_file)

        content_lines = _file_handler.read_file(test_file)
        lines = content_lines.splitlines(keepends=True)

        new_content = "\n== Inserted Section\n\nNew content\n"
        new_lines = (
            lines[:end_with_children]
            + [new_content]
            + lines[end_with_children:]
        )

        _file_handler.write_file(test_file, "".join(new_lines))

        # Re-parse
        doc_new = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc_new])

        # Verify all children are preserved
        section_a_new = index_new.get_section("test:section-a")
        assert len(section_a_new.children) == 1
        level2 = section_a_new.children[0]
        assert level2.title == "Level 2 Child"
        assert len(level2.children) == 1
        level3 = level2.children[0]
        assert level3.title == "Level 3 Child"
        assert len(level3.children) == 1
        level4 = level3.children[0]
        assert level4.title == "Level 4 Child"

    def test_insert_after_multiple_children(self, tmp_path: Path):
        """Insert after section with multiple children at same level."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

=== Child 1

Content 1

=== Child 2

Content 2

=== Child 3

Content 3

== Section B
""",
            encoding="utf-8",
        )

        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])

        section_a = index.get_section("test:section-a")
        assert len(section_a.children) == 3

        from dacli.api.manipulation import _file_handler, _get_section_end_with_children

        end_with_children = _get_section_end_with_children(section_a, test_file)

        content_lines = _file_handler.read_file(test_file)
        lines = content_lines.splitlines(keepends=True)

        new_content = "\n== Inserted Section\n\nNew\n"
        new_lines = (
            lines[:end_with_children]
            + [new_content]
            + lines[end_with_children:]
        )

        _file_handler.write_file(test_file, "".join(new_lines))

        # Re-parse
        doc_new = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc_new])

        # Verify all 3 children are preserved
        section_a_new = index_new.get_section("test:section-a")
        assert len(section_a_new.children) == 3
        assert section_a_new.children[0].title == "Child 1"
        assert section_a_new.children[1].title == "Child 2"
        assert section_a_new.children[2].title == "Child 3"


class TestInsertAfterWithoutChildren:
    """Test that insert 'after' still works for sections without children (regression)."""

    def test_insert_after_leaf_section(self, tmp_path: Path):
        """Insert after a section with no children should work correctly."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

== Section B

Content B
""",
            encoding="utf-8",
        )

        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])

        section_a = index.get_section("test:section-a")
        assert section_a is not None
        assert len(section_a.children) == 0

        from dacli.api.manipulation import _file_handler, _get_section_end_with_children

        # Insert after Section A (no children)
        end_with_children = _get_section_end_with_children(section_a, test_file)

        content_lines = _file_handler.read_file(test_file)
        lines = content_lines.splitlines(keepends=True)

        new_content = "\n== Section A.5\n\nInserted\n"
        new_lines = (
            lines[:end_with_children]
            + [new_content]
            + lines[end_with_children:]
        )

        _file_handler.write_file(test_file, "".join(new_lines))

        # Re-parse
        doc_new = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc_new])

        # Verify new section exists
        section_a5 = index_new.get_section("test:section-a5")
        assert section_a5 is not None


class TestInsertBeforeUnaffected:
    """Test that insert 'before' is not affected by the fix (regression)."""

    def test_insert_before_with_children(self, tmp_path: Path):
        """Insert 'before' should not be affected by the children fix."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

=== Subsection A1

Child

== Section B
""",
            encoding="utf-8",
        )

        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])

        section_a = index.get_section("test:section-a")

        from dacli.api.manipulation import _file_handler

        # Insert BEFORE Section A (should use start_line, not end_line)
        start_line = section_a.source_location.line

        content_lines = _file_handler.read_file(test_file)
        lines = content_lines.splitlines(keepends=True)

        new_content = "\n== Section Before A\n\nInserted before\n"
        new_lines = (
            lines[: start_line - 1]
            + [new_content]
            + lines[start_line - 1 :]
        )

        _file_handler.write_file(test_file, "".join(new_lines))

        # Re-parse
        doc_new = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc_new])

        # Verify Section A still has its child
        section_a_new = index_new.get_section("test:section-a")
        assert section_a_new is not None
        assert len(section_a_new.children) == 1


class TestInsertAppendUnaffected:
    """Test that insert 'append' is not affected (appends to direct content)."""

    def test_append_adds_before_children(self, tmp_path: Path):
        """Append should add content at end of direct content, before children."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text(
            """= Document

== Section A

Content A

=== Subsection A1

Child
""",
            encoding="utf-8",
        )

        parser = AsciidocStructureParser(base_path=tmp_path)
        index = StructureIndex()
        doc = parser.parse_file(test_file)
        index.build_from_documents([doc])

        section_a = index.get_section("test:section-a")

        from dacli.api.manipulation import _file_handler, _get_section_end_line

        # Append to Section A (should add before children)
        end_line = _get_section_end_line(section_a, test_file)

        content_lines = _file_handler.read_file(test_file)
        lines = content_lines.splitlines(keepends=True)

        new_content = "\nAppended content\n"
        new_lines = (
            lines[: end_line - 1]
            + [new_content]
            + lines[end_line - 1 :]
        )

        _file_handler.write_file(test_file, "".join(new_lines))

        # Re-parse
        doc_new = parser.parse_file(test_file)
        index_new = StructureIndex()
        index_new.build_from_documents([doc_new])

        # Verify child is still there
        section_a_new = index_new.get_section("test:section-a")
        assert section_a_new is not None
        assert len(section_a_new.children) == 1
        assert section_a_new.children[0].title == "Subsection A1"
