"""Tests for Markdown Parser.

Tests are organized by acceptance criteria from 04_markdown_parser.adoc.
"""

import tempfile
from pathlib import Path


class TestMarkdownParserBasic:
    """Basic parser instantiation tests."""

    def test_parser_can_be_instantiated(self):
        """Parser can be created."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
        assert parser is not None

    def test_parse_file_returns_markdown_document(self):
        """parse_file returns a MarkdownDocument."""
        from mcp_server.markdown_parser import MarkdownDocument, MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Title ###\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.sections[0].title == "Title"


class TestHeadingPaths:
    """Test hierarchical path generation for headings."""

    def test_root_heading_path(self):
        """Root heading has correct path."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Haupttitel\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        assert doc.sections[0].path == "/haupttitel"

    def test_nested_heading_paths(self):
        """Nested headings have correct hierarchical paths."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
            doc = parser.parse_file(Path(f.name))

        root = doc.sections[0]
        assert root.path == "/haupttitel"
        assert root.children[0].path == "/haupttitel/unterkapitel-1"
        assert root.children[1].path == "/haupttitel/unterkapitel-2"
        assert root.children[1].children[0].path == "/haupttitel/unterkapitel-2/sub-unterkapitel"

    def test_path_slugification(self):
        """Paths are properly slugified (lowercase, dashes)."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# My Great Title!\n")
            f.flush()
            doc = parser.parse_file(Path(f.name))

        # Should be slugified
        assert doc.sections[0].path == "/my-great-title"


class TestSourceLocation:
    """Test source location tracking for headings."""

    def test_heading_has_source_location(self):
        """Headings have correct source location."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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


class TestFrontmatterParsing:
    """AC-MD-02: YAML Frontmatter is correctly parsed."""

    def test_parses_simple_frontmatter(self):
        """Simple string frontmatter is parsed."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        """Code block has correct parent section."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
            doc = parser.parse_file(Path(f.name))

        code_block = doc.elements[0]
        assert code_block.parent_section == "/root/code-section"

    def test_multiple_code_blocks(self):
        """Multiple code blocks are extracted."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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


class TestTableRecognition:
    """AC-MD-04: GFM tables are recognized as blocks."""

    def test_extracts_simple_table(self):
        """Simple table is extracted."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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


class TestFolderStructure:
    """AC-MD-05: Folder hierarchy is correctly mapped."""

    def test_parse_folder_returns_folder_document(self):
        """parse_folder returns a FolderDocument."""
        from mcp_server.markdown_parser import FolderDocument, MarkdownParser

        parser = MarkdownParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Root\n")

            doc = parser.parse_folder(folder)

        assert isinstance(doc, FolderDocument)

    def test_parses_single_file_in_folder(self):
        """Single file in folder is parsed."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Root Document\n")

            doc = parser.parse_folder(folder)

        assert len(doc.documents) == 1
        assert doc.documents[0].title == "Root Document"

    def test_parses_multiple_files_in_folder(self):
        """Multiple files in folder are parsed."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "index.md").write_text("# Index\n")
            (folder / "chapter.md").write_text("# Chapter\n")

            doc = parser.parse_folder(folder)

        assert len(doc.documents) == 2

    def test_parses_nested_folders(self):
        """Nested folders are parsed recursively."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "a_first.md").write_text("# A First\n")
            (folder / "README.md").write_text("# README\n")
            (folder / "z_last.md").write_text("# Z Last\n")

            doc = parser.parse_folder(folder)

        assert doc.documents[0].title == "README"

    def test_index_comes_first(self):
        """index.md comes before other files."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "a_first.md").write_text("# A First\n")
            (folder / "index.md").write_text("# Index\n")
            (folder / "z_last.md").write_text("# Z Last\n")

            doc = parser.parse_folder(folder)

        assert doc.documents[0].title == "Index"

    def test_mixed_prefixes_and_names(self):
        """Mixed numeric prefixes and plain names are sorted correctly."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        """get_section returns correct section."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
        content = """# Root

## Chapter
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        section = parser.get_section(doc, "/root/chapter")
        assert section is not None
        assert section.title == "Chapter"

    def test_get_section_returns_none_for_invalid_path(self):
        """get_section returns None for invalid path."""
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()

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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
        from mcp_server.markdown_parser import MarkdownParser

        parser = MarkdownParser()
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
