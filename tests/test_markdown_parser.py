"""Tests for Markdown Parser.

Tests are organized by acceptance criteria from 04_markdown_parser.adoc.
"""

import tempfile
from pathlib import Path


class TestMarkdownStructureParserBasic:
    """Basic parser instantiation tests."""

    def test_parser_can_be_instantiated(self):
        """Parser can be created."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        assert parser is not None

    def test_parse_file_returns_markdown_document(self):
        """parse_file returns a MarkdownDocument."""
        from dacli.markdown_parser import MarkdownDocument, MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Test\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert isinstance(doc, MarkdownDocument)


class TestHeadingExtraction:
    """AC-MD-01: Headings are correctly extracted."""

    def test_extracts_single_h1_heading(self):
        """Single H1 heading is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Main Title\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.title == "Main Title"
        assert len(doc.sections) == 1
        assert doc.sections[0].title == "Main Title"
        assert doc.sections[0].level == 1

    def test_extracts_multiple_headings(self):
        """Multiple headings at different levels are extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Haupttitel

## Unterkapitel 1

Text...

## Unterkapitel 2

### Sub-Unterkapitel
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        # Should have 4 sections total
        assert doc.title == "Haupttitel"
        assert len(doc.sections) == 1  # Root section
        root = doc.sections[0]
        assert root.title == "Haupttitel"
        assert len(root.children) == 2  # Two H2 children

        child1 = root.children[0]
        assert child1.title == "Unterkapitel 1"
        assert child1.level == 2

        child2 = root.children[1]
        assert child2.title == "Unterkapitel 2"
        assert child2.level == 2
        assert len(child2.children) == 1  # One H3 child

        grandchild = child2.children[0]
        assert grandchild.title == "Sub-Unterkapitel"
        assert grandchild.level == 3

    def test_heading_levels_1_to_6(self):
        """All heading levels from 1 to 6 are supported."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# H1
## H2
### H3
#### H4
##### H5
###### H6
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        # Verify all levels are captured
        def count_sections(sections, level):
            count = 0
            for s in sections:
                if s.level == level:
                    count += 1
                count += count_sections(s.children, level)
            return count

        for level in range(1, 7):
            assert count_sections(doc.sections, level) == 1

    def test_heading_with_trailing_hashes(self):
        """Trailing hashes in headings are stripped."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Title ###\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.sections[0].title == "Title"


class TestHeadingPaths:
    """Test hierarchical path generation for headings (with file prefix, Issue #130, ADR-008)."""

    def test_root_heading_path(self):
        """Root heading has file prefix as path."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Haupttitel\n")
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        # Document title (H1) has file prefix as path (Issue #130, ADR-008)
        assert doc.sections[0].path == file_prefix

    def test_nested_heading_paths(self):
        """Nested headings have file-prefixed hierarchical paths."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Haupttitel

## Unterkapitel 1

## Unterkapitel 2

### Sub-Unterkapitel
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        root = doc.sections[0]
        # H1 (document title) has file prefix as path (Issue #130, ADR-008)
        assert root.path == file_prefix
        # H2 sections have file-prefix:slug paths
        assert root.children[0].path == f"{file_prefix}:unterkapitel-1"
        assert root.children[1].path == f"{file_prefix}:unterkapitel-2"
        # H3+ sections have file-prefix:parent.slug format
        assert root.children[1].children[0].path == f"{file_prefix}:unterkapitel-2.sub-unterkapitel"

    def test_path_slugification(self):
        """Paths are properly slugified (lowercase, dashes)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# My Great Title!\n")
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        # Document title has file prefix as path (Issue #130, ADR-008)
        assert doc.sections[0].path == file_prefix

    def test_duplicate_heading_titles_get_disambiguated_paths(self):
        """Test that headings with same title at same level get disambiguated paths.

        Issue #123: When multiple headings have the same title, paths should
        be automatically disambiguated within file-prefixed paths.
        """
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document Title

## Introduction

First introduction content.

## Details

Some details.

## Introduction

Second introduction content.

## Introduction

Third introduction content.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        root = doc.sections[0]
        # First occurrence keeps original path with file prefix
        assert root.children[0].path == f"{file_prefix}:introduction"
        # Subsequent duplicates get numbered suffix
        assert root.children[2].path == f"{file_prefix}:introduction-2"
        assert root.children[3].path == f"{file_prefix}:introduction-3"

    def test_duplicate_nested_heading_paths(self):
        """Test that duplicate titles in nested headings also get disambiguated.

        Issue #123: Disambiguation should work at all nesting levels.
        """
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Parent

### Details

First details.

### Details

Second details.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        root = doc.sections[0]
        parent = root.children[0]
        # First occurrence keeps original path with file prefix
        assert parent.children[0].path == f"{file_prefix}:parent.details"
        # Second occurrence gets numbered suffix
        assert parent.children[1].path == f"{file_prefix}:parent.details-2"

    def test_same_title_different_parents_no_conflict(self):
        """Test that same titles under different parents don't conflict.

        Issue #123: 'parent1.details' and 'parent2.details' are different paths.
        """
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Parent 1

### Details

Parent 1 details.

## Parent 2

### Details

Parent 2 details.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        root = doc.sections[0]
        # Both 'Details' sections keep their original path (different parents)
        assert root.children[0].children[0].path == f"{file_prefix}:parent-1.details"
        assert root.children[1].children[0].path == f"{file_prefix}:parent-2.details"


class TestSourceLocation:
    """Test source location tracking for headings."""

    def test_heading_has_source_location(self):
        """Headings have correct source location."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

## Chapter
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        root = doc.sections[0]
        assert root.source_location.line == 1
        assert root.source_location.file == Path(f.name)

        chapter = root.children[0]
        assert chapter.source_location.line == 3

    def test_section_has_end_line(self):
        """Sections have end_line calculated."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

Some content.

## Chapter

Chapter content.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        root = doc.sections[0]
        assert root.source_location.end_line is not None

    def test_section_end_line_is_before_next_section(self):
        """Section end_line is correctly calculated."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

## Chapter 1

Content 1.

## Chapter 2

Content 2.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        root = doc.sections[0]
        chapter1 = root.children[0]
        chapter2 = root.children[1]

        # Chapter 1 ends just before Chapter 2 starts
        assert chapter1.source_location.end_line == chapter2.source_location.line - 1


class TestFrontmatterParsing:
    """AC-MD-02: YAML Frontmatter is correctly parsed."""

    def test_parses_simple_frontmatter(self):
        """Simple string frontmatter is parsed."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
title: Mein Dokument
author: Max Mustermann
---

# Content
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.frontmatter["title"] == "Mein Dokument"
        assert doc.frontmatter["author"] == "Max Mustermann"

    def test_parses_list_in_frontmatter(self):
        """List values in frontmatter are parsed."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
tags: [design, architecture]
---

# Content
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.frontmatter["tags"] == ["design", "architecture"]
        assert len(doc.frontmatter["tags"]) == 2

    def test_parses_nested_object_in_frontmatter(self):
        """Nested objects in frontmatter are parsed."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
author:
  name: Max
  email: max@example.com
---

# Content
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.frontmatter["author"]["name"] == "Max"
        assert doc.frontmatter["author"]["email"] == "max@example.com"

    def test_frontmatter_title_overrides_heading(self):
        """Title from frontmatter takes precedence over H1."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
title: Frontmatter Title
---

# Heading Title
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.title == "Frontmatter Title"

    def test_no_frontmatter_is_empty_dict(self):
        """Document without frontmatter has empty frontmatter dict."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Just a heading
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.frontmatter == {}

    def test_invalid_frontmatter_is_empty_dict(self):
        """Invalid YAML in frontmatter results in empty dict (with warning)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
invalid: [not closed
---

# Content
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        # Should not raise, just return empty frontmatter
        assert doc.frontmatter == {}

    def test_headings_after_frontmatter_have_correct_line_numbers(self):
        """Line numbers account for frontmatter offset."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """---
title: Test
---

# Heading
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        # Heading is on line 5 (after frontmatter)
        assert doc.sections[0].source_location.line == 5


class TestCodeBlockExtraction:
    """AC-MD-03: Fenced code blocks are extracted."""

    def test_extracts_code_block_with_language(self):
        """Code block with language is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code Examples

```python
def hello():
    print("Hello, World!")
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        code_block = doc.elements[0]
        assert code_block.type == "code"
        assert code_block.attributes["language"] == "python"

    def test_code_block_source_location(self):
        """Code block has correct source location."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

```javascript
console.log("test");
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        code_block = doc.elements[0]
        assert code_block.source_location.line == 3  # Line of opening fence
        assert code_block.source_location.file == Path(f.name)

    def test_code_block_without_language(self):
        """Code block without language has empty language attribute."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code

```
plain text
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        assert doc.elements[0].attributes.get("language") is None

    def test_code_block_parent_section(self):
        """Code block has correct parent section with file prefix."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Root

## Code Section

```python
code
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        code_block = doc.elements[0]
        # Parent section now has file prefix (Issue #130, ADR-008)
        assert code_block.parent_section == f"{file_prefix}:code-section"

    def test_multiple_code_blocks(self):
        """Multiple code blocks are extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Examples

```python
python code
```

```javascript
javascript code
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 2
        assert doc.elements[0].attributes["language"] == "python"
        assert doc.elements[1].attributes["language"] == "javascript"

    def test_code_block_with_tilde_fence(self):
        """Code block with tilde fence is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code

~~~ruby
puts "hello"
~~~
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        assert doc.elements[0].attributes["language"] == "ruby"

    def test_unclosed_code_block_logs_warning(self, caplog):
        """Unclosed code block at end of file logs a warning."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code

```python
def hello():
    print("Hello")
"""  # Note: Missing closing fence

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            import logging
            with caplog.at_level(logging.WARNING):
                doc = parser.parse_file(Path(f.name))

        # Code block should not be created
        assert len(doc.elements) == 0

        # Warning should be logged
        assert "Unclosed code block" in caplog.text
        assert "line 3" in caplog.text
        assert "will be ignored" in caplog.text


class TestCodeBlockContent:
    """Code block content extraction per spec line 236."""

    def test_code_block_content_is_extracted(self):
        """Code block content is stored in attributes."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code Examples

```python
def hello():
    print("Hello, World!")
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        code_block = doc.elements[0]
        assert "content" in code_block.attributes
        assert code_block.attributes["content"] == 'def hello():\n    print("Hello, World!")'

    def test_multiline_code_content_preserved(self):
        """Multi-line code content is preserved with newlines."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Multi-line

```javascript
function test() {
    const x = 1;
    const y = 2;
    return x + y;
}
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        code_block = doc.elements[0]
        expected = """function test() {
    const x = 1;
    const y = 2;
    return x + y;
}"""
        assert code_block.attributes["content"] == expected

    def test_empty_code_block_has_empty_content(self):
        """Empty code block has empty string content."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Empty

```python
```
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        code_block = doc.elements[0]
        assert code_block.attributes["content"] == ""


class TestTableRecognition:
    """AC-MD-04: GFM tables are recognized as blocks."""

    def test_extracts_simple_table(self):
        """Simple table is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Data

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        table = doc.elements[0]
        assert table.type == "table"
        assert table.attributes["columns"] == 3

    def test_table_row_count(self):
        """Table has correct row count (excluding header)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Data

| A | B |
|---|---|
| 1 | 2 |
| 3 | 4 |
| 5 | 6 |
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        table = doc.elements[0]
        assert table.attributes["rows"] == 3

    def test_table_source_location(self):
        """Table has correct source location."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

Some text.

| A | B |
|---|---|
| 1 | 2 |
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        table = doc.elements[0]
        assert table.source_location.line == 5  # First line of table


class TestImageExtraction:
    """Test image element extraction."""

    def test_extracts_image(self):
        """Image is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Images

![Alt text](path/to/image.png)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        image = doc.elements[0]
        assert image.type == "image"
        assert image.attributes["alt"] == "Alt text"
        assert image.attributes["src"] == "path/to/image.png"

    def test_image_with_title(self):
        """Image with title is extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Images

![Diagram](diagram.png "A diagram")
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        image = doc.elements[0]
        assert image.attributes["title"] == "A diagram"

    def test_image_source_location(self):
        """Image has correct source location."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

![img](test.png)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        image = doc.elements[0]
        assert image.source_location.line == 3


class TestListExtraction:
    """Tests for list element extraction."""

    def test_extracts_unordered_list(self):
        """Test that unordered lists (* or -) are extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Lists

* Item one
* Item two
* Item three
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        unordered = [e for e in list_elements if e.attributes.get("list_type") == "unordered"]
        assert len(unordered) >= 1

    def test_extracts_ordered_list(self):
        """Test that ordered lists (1.) are extracted."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Steps

1. First step
2. Second step
3. Third step
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        ordered = [e for e in list_elements if e.attributes.get("list_type") == "ordered"]
        assert len(ordered) >= 1

    def test_list_has_parent_section(self):
        """Test that list element has correct parent section."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## My Lists

* Item A
* Item B
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        assert len(list_elements) >= 1
        assert "my-lists" in list_elements[0].parent_section

    def test_list_source_location(self):
        """Test that list has correct source location."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Lists

* First item
* Second item
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        assert len(list_elements) >= 1
        assert list_elements[0].source_location.line == 5  # Line of "* First item"


class TestFolderStructure:
    """AC-MD-05: Folder hierarchy is correctly mapped."""

    def test_parse_folder_returns_folder_document(self):
        """parse_folder returns a FolderDocument."""
        from dacli.markdown_parser import FolderDocument, MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Root\n")

            doc = parser.parse_folder(folder)

        assert isinstance(doc, FolderDocument)

    def test_parses_single_file_in_folder(self):
        """Single file in folder is parsed."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Root Document\n")

            doc = parser.parse_folder(folder)

        assert len(doc.documents) == 1
        assert doc.documents[0].title == "Root Document"

    def test_parses_multiple_files_in_folder(self):
        """Multiple files in folder are parsed."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Index\n")
            (folder / "chapter.md").write_text("# Chapter\n")

            doc = parser.parse_folder(folder)

        assert len(doc.documents) == 2

    def test_parses_nested_folders(self):
        """Nested folders are parsed recursively."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Root\n")
            subdir = folder / "01_intro"
            subdir.mkdir()
            (subdir / "index.md").write_text("# Intro\n")
            (subdir / "01_details.md").write_text("# Details\n")

            doc = parser.parse_folder(folder)

        assert len(doc.documents) == 3

    def test_folder_structure_order(self):
        """Files are in correct order (index first, then sorted)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Index\n")
            subdir = folder / "01_intro"
            subdir.mkdir()
            (subdir / "index.md").write_text("# Intro\n")
            (subdir / "01_details.md").write_text("# Details\n")
            (folder / "02_chapter.md").write_text("# Chapter\n")

            doc = parser.parse_folder(folder)

        # Expected order: index.md, 01_intro/index.md, 01_intro/01_details.md, 02_chapter.md
        assert doc.documents[0].title == "Index"
        assert doc.documents[1].title == "Intro"
        assert doc.documents[2].title == "Details"
        assert doc.documents[3].title == "Chapter"


class TestNumericPrefixSorting:
    """AC-MD-06: Numeric prefixes are correctly sorted."""

    def test_numeric_prefixes_sorted_correctly(self):
        """Files with numeric prefixes are sorted numerically."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "README.md").write_text("# README\n")
            (folder / "10_z.md").write_text("# Ten\n")
            (folder / "2_b.md").write_text("# Two\n")
            (folder / "1_a.md").write_text("# One\n")

            doc = parser.parse_folder(folder)

        # Expected order: README.md, 1_a.md, 2_b.md, 10_z.md
        assert len(doc.documents) == 4
        assert doc.documents[0].title == "README"
        assert doc.documents[1].title == "One"
        assert doc.documents[2].title == "Two"
        assert doc.documents[3].title == "Ten"

    def test_readme_comes_first(self):
        """README.md comes before other files."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "a_first.md").write_text("# A First\n")
            (folder / "README.md").write_text("# README\n")
            (folder / "z_last.md").write_text("# Z Last\n")

            doc = parser.parse_folder(folder)

        assert doc.documents[0].title == "README"

    def test_index_comes_first(self):
        """index.md comes before other files."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "a_first.md").write_text("# A First\n")
            (folder / "index.md").write_text("# Index\n")
            (folder / "z_last.md").write_text("# Z Last\n")

            doc = parser.parse_folder(folder)

        assert doc.documents[0].title == "Index"

    def test_mixed_prefixes_and_names(self):
        """Mixed numeric prefixes and plain names are sorted correctly."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "01_intro.md").write_text("# Intro\n")
            (folder / "appendix.md").write_text("# Appendix\n")
            (folder / "02_main.md").write_text("# Main\n")

            doc = parser.parse_folder(folder)

        # Numeric prefixes should come first, then alphabetic
        assert doc.documents[0].title == "Intro"
        assert doc.documents[1].title == "Main"
        assert doc.documents[2].title == "Appendix"


class TestInterfaceMethods:
    """Test get_section and get_elements interface methods."""

    def test_get_section_returns_section_by_path(self):
        """get_section returns correct section with file-prefixed path."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Root

## Chapter
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)
            file_prefix = file_path.stem
            doc = parser.parse_file(file_path)

        # Use file-prefixed path (Issue #130, ADR-008)
        section = parser.get_section(doc, f"{file_prefix}:chapter")
        assert section is not None
        assert section.title == "Chapter"

    def test_get_section_returns_none_for_invalid_path(self):
        """get_section returns None for invalid path."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Title\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        section = parser.get_section(doc, "/nonexistent")
        assert section is None

    def test_get_elements_returns_all_elements(self):
        """get_elements returns all elements."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

```python
code
```

![img](test.png)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        elements = parser.get_elements(doc)
        assert len(elements) == 2

    def test_get_elements_filters_by_type(self):
        """get_elements filters by type."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

```python
code
```

![img](test.png)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        code_elements = parser.get_elements(doc, "code")
        assert len(code_elements) == 1
        assert code_elements[0].type == "code"


class TestSetextHeadingWarnings:
    """Tests for Setext heading detection and warnings (Issue #124).

    Setext headings are not supported but should trigger warnings to help
    users understand why their document structure might look incorrect.
    """

    def test_setext_h1_triggers_warning(self, caplog):
        """Setext H1 (===) triggers a warning."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# ATX Heading

Some content.

Setext Title
============

More content.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            with caplog.at_level(logging.WARNING):
                parser.parse_file(Path(f.name))

        # Warning should be logged
        assert "Setext" in caplog.text or "setext" in caplog.text
        # Line number should be in the warning (format: :5 or :6)
        assert ":5" in caplog.text or ":6" in caplog.text

    def test_setext_h2_triggers_warning(self, caplog):
        """Setext H2 (---) triggers a warning."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Main Title

Setext Section
--------------

Content here.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            with caplog.at_level(logging.WARNING):
                parser.parse_file(Path(f.name))

        # Warning should be logged
        assert "Setext" in caplog.text or "setext" in caplog.text

    def test_setext_heading_not_added_as_section(self, caplog):
        """Setext headings should NOT be added as sections."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Main Title

## ATX Section

Setext Title
============

Content.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            with caplog.at_level(logging.WARNING):
                doc = parser.parse_file(Path(f.name))

        # Should only have 2 sections: Main Title and ATX Section
        all_sections = []

        def collect(sections):
            for s in sections:
                all_sections.append(s.title)
                collect(s.children)

        collect(doc.sections)
        assert "Main Title" in all_sections
        assert "ATX Section" in all_sections
        assert "Setext Title" not in all_sections

    def test_horizontal_rule_does_not_trigger_warning(self, caplog):
        """Horizontal rule (--- with blank before) should NOT warn."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

Some content.

---

More content after horizontal rule.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            with caplog.at_level(logging.WARNING):
                parser.parse_file(Path(f.name))

        # No Setext warning should be logged (horizontal rule is different)
        assert "Setext" not in caplog.text and "setext" not in caplog.text

    def test_warning_includes_file_path(self, caplog):
        """Warning should include the file path."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """Setext Title
============
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

            with caplog.at_level(logging.WARNING):
                parser.parse_file(file_path)

        # Warning should mention the file
        assert str(file_path) in caplog.text or file_path.name in caplog.text

    def test_warning_suggests_atx_style(self, caplog):
        """Warning should suggest using ATX-style headings."""
        import logging

        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """Setext Title
============
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()

            with caplog.at_level(logging.WARNING):
                parser.parse_file(Path(f.name))

        # Warning should suggest ATX style
        assert "ATX" in caplog.text or "#" in caplog.text


class TestFilePrefixPaths:
    """Tests for file-prefix path format (Issue #130, ADR-008).

    According to ADR-008, paths must include the relative file path as prefix:
    - Document title (level 0): <file-prefix> (e.g., "guides/getting-started")
    - Sections: <file-prefix>:<section-path> (e.g., "guides/getting-started:installation")

    This ensures unique paths across documents in a project.
    """

    def test_document_title_path_is_file_prefix(self):
        """Test that document title path equals relative file path without extension."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Document Title

## Chapter One

Content here.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            test_file = base_path / "test_doc.md"
            test_file.write_text(content)

            parser = MarkdownStructureParser(base_path=base_path)
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            # Document title path should be the file path (relative to base_path, no extension)
            assert root.path == "test_doc"

    def test_chapter_path_includes_file_prefix(self):
        """Test that chapter paths include file prefix with colon separator."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Document Title

## Chapter One

First chapter.

## Chapter Two

Second chapter.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            test_file = base_path / "test_doc.md"
            test_file.write_text(content)

            parser = MarkdownStructureParser(base_path=base_path)
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            # Level 2 sections: file-prefix:slug
            assert root.children[0].path == "test_doc:chapter-one"
            assert root.children[1].path == "test_doc:chapter-two"

    def test_subsection_path_includes_file_prefix(self):
        """Test that subsection paths include file prefix and full hierarchy."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Document Title

## Chapter

### Subsection

Content here.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            test_file = base_path / "test_doc.md"
            test_file.write_text(content)

            parser = MarkdownStructureParser(base_path=base_path)
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            subsection = root.children[0].children[0]
            # Level 3+ sections: file-prefix:parent.child
            assert subsection.path == "test_doc:chapter.subsection"

    def test_file_prefix_with_subdirectory(self):
        """Test that file prefix includes subdirectory path."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Nested Document

## Section One

Content here.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            subdir = base_path / "guides"
            subdir.mkdir()
            test_file = subdir / "nested_doc.md"
            test_file.write_text(content)

            parser = MarkdownStructureParser(base_path=base_path)
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            # Path should include subdirectory
            assert root.path == "guides/nested_doc"
            assert root.children[0].path == "guides/nested_doc:section-one"

    def test_duplicate_sections_still_disambiguated_with_file_prefix(self):
        """Test that duplicate sections are disambiguated within file-prefixed paths."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Document Title

## Introduction

First intro.

## Introduction

Second intro with same title.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            test_file = base_path / "dup_with_prefix.md"
            test_file.write_text(content)

            parser = MarkdownStructureParser(base_path=base_path)
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            assert root.path == "dup_with_prefix"
            # Duplicate sections get -2, -3 suffix within file-prefixed path
            assert root.children[0].path == "dup_with_prefix:introduction"
            assert root.children[1].path == "dup_with_prefix:introduction-2"

    def test_backwards_compatible_no_base_path(self):
        """Test that parser without base_path still works (derives from file path)."""
        from dacli.markdown_parser import MarkdownStructureParser

        content = """# Document Title

## Chapter

Content.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "my_doc.md"
            test_file.write_text(content)

            # Parser without explicit base_path - should derive from file's parent
            parser = MarkdownStructureParser()
            doc = parser.parse_file(test_file)

            root = doc.sections[0]
            # Should still have file-based path
            assert root.path == "my_doc"
            assert root.children[0].path == "my_doc:chapter"


class TestElementEndLine:
    """Tests for element end_line calculation (Issue #128).

    Elements should have end_line set correctly for:
    - Code blocks: end_line is the closing fence
    - Tables: end_line is the last row of the table
    - Images: end_line equals start_line (single line)
    - Lists: end_line is the last line of the list
    """

    def test_code_block_has_end_line(self):
        """Test that code blocks have end_line set (Issue #128)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

```python
def hello():
    print("Hello")
```
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        code_block = doc.elements[0]
        assert code_block.source_location.line == 3  # Opening fence
        assert code_block.source_location.end_line == 6  # Closing fence

    def test_table_has_end_line(self):
        """Test that tables have end_line set (Issue #128)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

| Col A | Col B |
|-------|-------|
| A1    | B1    |
| A2    | B2    |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        table_elements = [e for e in doc.elements if e.type == "table"]
        assert len(table_elements) == 1
        assert table_elements[0].source_location.line == 3  # First table row
        assert table_elements[0].source_location.end_line == 6  # Last table row

    def test_image_has_end_line_equal_to_start(self):
        """Test that images have end_line equal to start_line (Issue #128)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

![Alt text](image.png)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        image_elements = [e for e in doc.elements if e.type == "image"]
        assert len(image_elements) == 1
        assert image_elements[0].source_location.line == 3
        assert image_elements[0].source_location.end_line == 3  # Single line

    def test_list_has_end_line(self):
        """Test that lists have end_line set (Issue #128)."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Title

- Item 1
- Item 2
- Item 3

Next paragraph.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        assert len(list_elements) == 1
        assert list_elements[0].source_location.line == 3  # First list item
        assert list_elements[0].source_location.end_line == 5  # Last list item
