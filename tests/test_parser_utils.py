"""Tests for parser utility functions."""

import pytest

from dacli.models import Section, SourceLocation
from dacli.parser_utils import collect_all_sections, find_section_by_path, slugify


class TestSlugify:
    """Tests for the slugify function."""

    def test_basic_text(self):
        """Test basic text conversion."""
        assert slugify("Hello World") == "hello-world"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert slugify("Hello! World?") == "hello-world"
        assert slugify("Test (with) brackets") == "test-with-brackets"

    def test_multiple_spaces(self):
        """Test that multiple spaces become single dash."""
        assert slugify("Hello   World") == "hello-world"

    def test_underscores_converted(self):
        """Test that underscores are converted to dashes."""
        assert slugify("hello_world") == "hello-world"

    def test_multiple_dashes_collapsed(self):
        """Test that multiple dashes are collapsed."""
        assert slugify("hello--world") == "hello-world"
        assert slugify("hello---world") == "hello-world"

    def test_leading_trailing_dashes_trimmed(self):
        """Test that leading/trailing dashes are trimmed."""
        assert slugify("-hello-") == "hello"
        assert slugify("  hello  ") == "hello"

    def test_unicode_preserved(self):
        """Test that Unicode characters are preserved."""
        assert slugify("Übersicht") == "übersicht"
        assert slugify("日本語") == "日本語"

    def test_empty_string(self):
        """Test empty string handling."""
        assert slugify("") == ""

    def test_only_special_chars(self):
        """Test string with only special characters."""
        assert slugify("!@#$%") == ""


class TestCollectAllSections:
    """Tests for the collect_all_sections function."""

    def _make_section(self, path: str, children: list[Section] = None) -> Section:
        """Helper to create a section."""
        return Section(
            title=path,
            path=path,
            level=path.count(".") + 1,
            source_location=SourceLocation(file="test.adoc", line=1),
            children=children or [],
        )

    def test_empty_list(self):
        """Test with empty section list."""
        result: list[Section] = []
        collect_all_sections([], result)
        assert result == []

    def test_flat_list(self):
        """Test with flat section list (no children)."""
        sections = [
            self._make_section("a"),
            self._make_section("b"),
            self._make_section("c"),
        ]
        result: list[Section] = []
        collect_all_sections(sections, result)
        assert len(result) == 3
        assert [s.path for s in result] == ["a", "b", "c"]

    def test_nested_sections(self):
        """Test with nested sections."""
        child1 = self._make_section("parent.child1")
        child2 = self._make_section("parent.child2")
        parent = self._make_section("parent", [child1, child2])

        result: list[Section] = []
        collect_all_sections([parent], result)

        assert len(result) == 3
        assert [s.path for s in result] == ["parent", "parent.child1", "parent.child2"]

    def test_deeply_nested(self):
        """Test with deeply nested sections."""
        grandchild = self._make_section("a.b.c")
        child = self._make_section("a.b", [grandchild])
        parent = self._make_section("a", [child])

        result: list[Section] = []
        collect_all_sections([parent], result)

        assert len(result) == 3
        assert [s.path for s in result] == ["a", "a.b", "a.b.c"]


class TestFindSectionByPath:
    """Tests for the find_section_by_path function."""

    def _make_section(self, path: str, children: list[Section] = None) -> Section:
        """Helper to create a section."""
        return Section(
            title=path,
            path=path,
            level=path.count(".") + 1,
            source_location=SourceLocation(file="test.adoc", line=1),
            children=children or [],
        )

    def test_empty_list(self):
        """Test with empty section list."""
        assert find_section_by_path([], "foo") is None

    def test_find_top_level(self):
        """Test finding top-level section."""
        sections = [
            self._make_section("a"),
            self._make_section("b"),
            self._make_section("c"),
        ]
        result = find_section_by_path(sections, "b")
        assert result is not None
        assert result.path == "b"

    def test_find_nested(self):
        """Test finding nested section."""
        child = self._make_section("parent.child")
        parent = self._make_section("parent", [child])

        result = find_section_by_path([parent], "parent.child")
        assert result is not None
        assert result.path == "parent.child"

    def test_find_deeply_nested(self):
        """Test finding deeply nested section."""
        grandchild = self._make_section("a.b.c")
        child = self._make_section("a.b", [grandchild])
        parent = self._make_section("a", [child])

        result = find_section_by_path([parent], "a.b.c")
        assert result is not None
        assert result.path == "a.b.c"

    def test_not_found(self):
        """Test when section is not found."""
        sections = [self._make_section("a"), self._make_section("b")]
        assert find_section_by_path(sections, "nonexistent") is None

    def test_partial_path_not_found(self):
        """Test that partial paths don't match."""
        child = self._make_section("parent.child")
        parent = self._make_section("parent", [child])

        # "parent.chi" should not match "parent.child"
        assert find_section_by_path([parent], "parent.chi") is None
