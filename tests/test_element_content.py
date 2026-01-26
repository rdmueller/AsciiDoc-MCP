"""Tests for Issue #159: Element Content Capture.

Tests parser content capture, API attributes inclusion, CLI flags,
and MCP tool parameters for element content.
"""

import tempfile
from pathlib import Path

import pytest

from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.markdown_parser import MarkdownStructureParser


class TestAsciidocContentCapture:
    """Test content capture in AsciiDoc parser."""

    def test_code_block_captures_content(self):
        """Code blocks should capture their content."""
        content = """= Document

== Section

[source,python]
----
def hello():
    print("world")
----
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".adoc", delete=False) as f:
            f.write(content)
            f.flush()
            parser = AsciidocStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        code_elem = doc.elements[0]
        assert code_elem.type == "code"
        assert "content" in code_elem.attributes
        assert 'def hello():' in code_elem.attributes["content"]
        assert 'print("world")' in code_elem.attributes["content"]

    def test_table_captures_content(self):
        """Tables should capture their content."""
        content = """= Document

== Section

|===
| Header 1 | Header 2
| Cell 1   | Cell 2
|===
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".adoc", delete=False) as f:
            f.write(content)
            f.flush()
            parser = AsciidocStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        table_elem = doc.elements[0]
        assert table_elem.type == "table"
        assert "content" in table_elem.attributes
        assert "Header 1" in table_elem.attributes["content"]
        assert "Cell 1" in table_elem.attributes["content"]

    def test_plantuml_captures_content(self):
        """PlantUML diagrams should capture their source."""
        content = """= Document

== Section

[plantuml,diagram,svg]
----
@startuml
Alice -> Bob: Hello
@enduml
----
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".adoc", delete=False) as f:
            f.write(content)
            f.flush()
            parser = AsciidocStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        diagram = doc.elements[0]
        assert diagram.type == "plantuml"
        assert "content" in diagram.attributes
        assert "@startuml" in diagram.attributes["content"]
        assert "Alice -> Bob" in diagram.attributes["content"]

    def test_list_captures_content(self):
        """Lists should capture their items."""
        content = """= Document

== Section

* Item 1
* Item 2
* Item 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".adoc", delete=False) as f:
            f.write(content)
            f.flush()
            parser = AsciidocStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        list_elem = doc.elements[0]
        assert list_elem.type == "list"
        assert "content" in list_elem.attributes
        assert "* Item 1" in list_elem.attributes["content"]
        assert "* Item 2" in list_elem.attributes["content"]


class TestMarkdownContentCapture:
    """Test content capture in Markdown parser."""

    def test_code_block_captures_content(self):
        """Markdown code blocks should capture content."""
        content = """# Document

## Section

```python
def hello():
    print("world")
```
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            parser = MarkdownStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        code_elem = doc.elements[0]
        assert code_elem.type == "code"
        assert "content" in code_elem.attributes
        assert 'def hello():' in code_elem.attributes["content"]

    def test_table_captures_content(self):
        """Markdown tables should capture content."""
        content = """# Document

## Section

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            parser = MarkdownStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        table_elem = doc.elements[0]
        assert table_elem.type == "table"
        assert "content" in table_elem.attributes
        assert "Header 1" in table_elem.attributes["content"]

    def test_list_captures_content(self):
        """Markdown lists should capture content."""
        content = """# Document

## Section

- Item 1
- Item 2
- Item 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            parser = MarkdownStructureParser(Path(f.name).parent)
            doc = parser.parse_file(Path(f.name))

        assert len(doc.elements) == 1
        list_elem = doc.elements[0]
        assert list_elem.type == "list"
        assert "content" in list_elem.attributes
        assert "- Item 1" in list_elem.attributes["content"]


class TestCliContentFlags:
    """Test CLI flags for content control."""

    def test_elements_without_include_content_has_no_attributes(self, cli_runner, temp_docs_dir):
        """Default: elements should not include attributes."""
        (temp_docs_dir / "test.adoc").write_text("""= Test

== Section

[source,bash]
----
echo "test"
----
""")
        result = cli_runner.invoke(["--docs-root", str(temp_docs_dir), "elements", "--type", "code"])
        assert result.exit_code == 0
        assert "attributes" not in result.output

    def test_elements_with_include_content_has_attributes(self, cli_runner, temp_docs_dir):
        """With --include-content: elements should include attributes."""
        (temp_docs_dir / "test.adoc").write_text("""= Test

== Section

[source,bash]
----
echo "test"
----
""")
        result = cli_runner.invoke([
            "--docs-root", str(temp_docs_dir),
            "elements", "--type", "code", "--include-content"
        ])
        assert result.exit_code == 0
        assert "attributes" in result.output
        assert "content" in result.output
        assert 'echo "test"' in result.output

    def test_content_limit_truncates_content(self, cli_runner, temp_docs_dir):
        """With --content-limit: content should be truncated."""
        (temp_docs_dir / "test.adoc").write_text("""= Test

== Section

[source,bash]
----
line 1
line 2
line 3
line 4
line 5
----
""")
        result = cli_runner.invoke([
            "--docs-root", str(temp_docs_dir),
            "elements", "--type", "code", "--include-content", "--content-limit", "2"
        ])
        assert result.exit_code == 0
        assert "line 1" in result.output
        assert "line 2" in result.output
        assert "line 3" not in result.output
        assert "line 4" not in result.output


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    from click.testing import CliRunner
    from dacli.cli import cli

    runner = CliRunner()

    class Runner:
        def invoke(self, args):
            return runner.invoke(cli, args)

    return Runner()


@pytest.fixture
def temp_docs_dir():
    """Create a temporary directory for test documents."""
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)
