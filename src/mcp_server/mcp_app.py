"""FastMCP Application for MCP Documentation Server.

This module provides the MCP server using FastMCP. It exposes tools for
document navigation, content access, search, and manipulation.

Tools:
    - get_structure: Get hierarchical document structure
    - get_section: Read content of a specific section
    - search: Search for content in documentation
    - get_elements: Get elements (code, tables, images)
    - update_section: Update section content
    - insert_content: Insert content relative to a section
"""

import logging
import sys
from pathlib import Path

from fastmcp import FastMCP

from mcp_server import __version__
from mcp_server.asciidoc_parser import AsciidocParser
from mcp_server.file_handler import FileReadError, FileSystemHandler, FileWriteError
from mcp_server.markdown_parser import MarkdownParser
from mcp_server.models import Document, Section
from mcp_server.structure_index import StructureIndex

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_mcp_server(docs_root: Path | str | None = None) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        docs_root: Root directory containing documentation files.
                   If None, uses current directory.

    Returns:
        Configured FastMCP instance with all tools registered.
    """
    # Resolve docs root
    if docs_root is None:
        docs_root = Path.cwd()
    elif isinstance(docs_root, str):
        docs_root = Path(docs_root)
    docs_root = docs_root.resolve()

    # Create server instance
    mcp = FastMCP(
        name="AsciiDoc MCP Server",
        version=__version__,
    )

    # Initialize components
    index = StructureIndex()
    file_handler = FileSystemHandler()
    asciidoc_parser = AsciidocParser(base_path=docs_root)
    markdown_parser = MarkdownParser()

    # Build initial index
    _build_index(docs_root, index, asciidoc_parser, markdown_parser)

    # Register tools
    @mcp.tool()
    def get_structure(max_depth: int | None = None) -> dict:
        """Get the hierarchical document structure.

        Use this tool to understand the layout of the documentation project.
        It returns a tree of sections with their paths, titles, and nesting levels.

        Args:
            max_depth: Maximum depth to return (None for unlimited).
                       Use 1 for top-level sections only, 2 for sections and
                       their direct children, etc.

        Returns:
            Document structure with 'sections' (hierarchical tree) and
            'total_sections' count.
        """
        return index.get_structure(max_depth)

    @mcp.tool()
    def get_section(path: str) -> dict | None:
        """Read the content of a specific section.

        Use this tool to retrieve the full content of a documentation section.
        The path is a hierarchical path using dot notation like
        'document-name.chapter-1.section-2'.

        Args:
            path: Hierarchical path to the section (e.g., 'my-doc.introduction.goals').
                  Paths use '.' as separator and include the document name.

        Returns:
            Section data including 'path', 'title', 'content', 'location',
            and 'format'. Returns dict with 'error' key if section not found.
        """
        # The index uses paths without leading slash
        normalized_path = path.lstrip("/")

        section = index.get_section(normalized_path)
        if section is None:
            return {"error": "Section not found", "path": normalized_path}

        # Read actual content from file
        try:
            file_content = file_handler.read_file(section.source_location.file)
            lines = file_content.splitlines()

            start_line = section.source_location.line - 1  # Convert to 0-based
            end_line = section.source_location.end_line
            if end_line is None:
                end_line = len(lines)

            content = "\n".join(lines[start_line:end_line])

            # Determine format
            file_ext = section.source_location.file.suffix.lower()
            doc_format = "asciidoc" if file_ext in (".adoc", ".asciidoc") else "markdown"

            return {
                "path": section.path,
                "title": section.title,
                "content": content,
                "location": {
                    "file": str(section.source_location.file),
                    "start_line": section.source_location.line,
                    "end_line": end_line,
                },
                "format": doc_format,
            }
        except FileReadError as e:
            return {"error": f"Failed to read section content: {e}"}

    @mcp.tool()
    def get_sections_at_level(level: int) -> dict:
        """Get all sections at a specific nesting level.

        Use this tool to retrieve all sections at a particular level of the
        document hierarchy. Level 1 represents chapters/top-level sections,
        level 2 represents sub-sections, etc.

        Args:
            level: Nesting level (1 = chapters, 2 = sections, 3 = sub-sections, etc.)

        Returns:
            Dictionary with 'level', 'sections' (list with path and title),
            and 'count'.
        """
        sections = index.get_sections_at_level(level)

        return {
            "level": level,
            "sections": [
                {
                    "path": s.path,
                    "title": s.title,
                }
                for s in sections
            ],
            "count": len(sections),
        }

    @mcp.tool()
    def search(
        query: str,
        scope: str | None = None,
        max_results: int = 50,
    ) -> dict:
        """Search for content in the documentation.

        Use this tool to find sections matching a search query.
        Currently searches section titles.

        Args:
            query: Search query string (case-insensitive by default).
            scope: Optional path prefix to limit search scope
                   (e.g., '/architecture' to search only in that section).
            max_results: Maximum number of results to return (default: 50).

        Returns:
            Search results with 'query', 'results' (list of matches with
            path, line, context, score), and 'total_results'.
        """
        results = index.search(
            query=query,
            scope=scope,
            case_sensitive=False,
            max_results=max_results,
        )

        return {
            "query": query,
            "results": [
                {
                    "path": r.path,
                    "line": r.line,
                    "context": r.context,
                    "score": r.score,
                }
                for r in results
            ],
            "total_results": len(results),
        }

    @mcp.tool()
    def get_elements(
        element_type: str | None = None,
        section_path: str | None = None,
    ) -> dict:
        """Get elements (code blocks, tables, images) from the documentation.

        Use this tool to find specific types of content elements within
        the documentation, such as code examples, tables, or diagrams.

        Args:
            element_type: Filter by type - 'code', 'table', 'image',
                          'diagram', 'list'. None returns all elements.
            section_path: Filter by section path (e.g., '/architecture').

        Returns:
            Dictionary with 'elements' (list of elements with type, location,
            preview) and 'count'.
        """
        elements = index.get_elements(
            element_type=element_type,
            section_path=section_path,
        )

        return {
            "elements": [
                {
                    "type": e.type,
                    "parent_section": e.parent_section,
                    "location": {
                        "file": str(e.source_location.file),
                        "start_line": e.source_location.line,
                        "end_line": e.source_location.end_line,
                    },
                    "preview": e.content[:100] if e.content else None,
                }
                for e in elements
            ],
            "count": len(elements),
        }

    @mcp.tool()
    def update_section(
        path: str,
        content: str,
        preserve_title: bool = True,
    ) -> dict:
        """Update the content of a section.

        Use this tool to modify the content of an existing documentation section.
        The change is written directly to the source file.

        Args:
            path: Hierarchical path to the section using dot notation
                  (e.g., 'my-doc.introduction').
            content: New section content. If preserve_title is True and content
                     doesn't start with a heading, the original title is preserved.
            preserve_title: Whether to preserve the original section title
                            (default: True). Set to False to replace everything.

        Returns:
            Success status with 'success', 'path', and 'location'.
        """
        # The index uses paths without leading slash
        normalized_path = path.lstrip("/")

        section = index.get_section(normalized_path)
        if section is None:
            return {"success": False, "error": f"Section '{normalized_path}' not found"}

        file_path = section.source_location.file
        start_line = section.source_location.line
        end_line = _get_section_end_line(section, file_path, file_handler)

        # Prepare content
        new_content = content
        if preserve_title:
            stripped_content = new_content.lstrip()
            has_explicit_title = stripped_content.startswith(
                "="
            ) or stripped_content.startswith("#")
            if not has_explicit_title:
                # Prepend the original title line
                file_ext = file_path.suffix.lower()
                if file_ext in (".adoc", ".asciidoc"):
                    level_markers = "=" * (section.level + 1)
                else:
                    level_markers = "#" * (section.level + 1)
                new_content = f"{level_markers} {section.title}\n\n{new_content}"

        # Ensure content ends with newline
        if not new_content.endswith("\n"):
            new_content += "\n"

        # Perform update
        try:
            file_handler.update_section(
                path=file_path,
                start_line=start_line,
                end_line=end_line,
                new_content=new_content,
            )
            return {
                "success": True,
                "path": normalized_path,
                "location": {
                    "file": str(file_path),
                    "line": start_line,
                },
            }
        except FileWriteError as e:
            return {
                "success": False,
                "error": f"Failed to write changes: {e}",
            }

    @mcp.tool()
    def insert_content(
        path: str,
        position: str,
        content: str,
    ) -> dict:
        """Insert content relative to a section.

        Use this tool to add new content before, after, or at the end of
        an existing section. This is useful for adding new sections or
        appending content.

        Args:
            path: Hierarchical path to the reference section using dot notation
                  (e.g., 'my-doc.introduction').
            position: Where to insert - 'before' (before section start),
                      'after' (after section end), or 'append' (at end of
                      section, before children).
            content: Content to insert.

        Returns:
            Success status with 'success' and 'inserted_at' location.
        """
        if position not in ("before", "after", "append"):
            return {
                "success": False,
                "error": f"Invalid position '{position}'. Use 'before', 'after', or 'append'.",
            }

        # The index uses paths without leading slash
        normalized_path = path.lstrip("/")

        section = index.get_section(normalized_path)
        if section is None:
            return {"success": False, "error": f"Section '{normalized_path}' not found"}

        file_path = section.source_location.file
        start_line = section.source_location.line
        end_line = _get_section_end_line(section, file_path, file_handler)

        # Prepare content
        insert_content = content
        if not insert_content.endswith("\n"):
            insert_content += "\n"

        try:
            file_content = file_handler.read_file(file_path)
            lines = file_content.splitlines(keepends=True)

            if position == "before":
                insert_line = start_line
                new_lines = lines[: start_line - 1] + [insert_content] + lines[start_line - 1 :]
            elif position == "after":
                insert_line = end_line + 1
                new_lines = lines[:end_line] + [insert_content] + lines[end_line:]
            else:  # append
                insert_line = end_line
                new_lines = lines[: end_line - 1] + [insert_content] + lines[end_line - 1 :]

            new_file_content = "".join(new_lines)
            file_handler.write_file(file_path, new_file_content)

            return {
                "success": True,
                "inserted_at": {
                    "file": str(file_path),
                    "line": insert_line,
                },
            }
        except (FileReadError, FileWriteError) as e:
            return {"success": False, "error": f"Failed to insert content: {e}"}

    return mcp


def _build_index(
    docs_root: Path,
    index: StructureIndex,
    asciidoc_parser: AsciidocParser,
    markdown_parser: MarkdownParser,
) -> None:
    """Build the structure index from documents in docs_root.

    Args:
        docs_root: Root directory containing documentation
        index: StructureIndex to populate
        asciidoc_parser: Parser for AsciiDoc files
        markdown_parser: Parser for Markdown files
    """
    documents: list[Document] = []

    # Find and parse AsciiDoc files
    for adoc_file in docs_root.rglob("*.adoc"):
        try:
            doc = asciidoc_parser.parse_file(adoc_file)
            documents.append(doc)
        except Exception as e:
            # Log but continue with other files
            logger.warning("Failed to parse %s: %s", adoc_file, e)

    # Find and parse Markdown files
    for md_file in docs_root.rglob("*.md"):
        # Skip common non-doc files
        if md_file.name in ("CLAUDE.md", "README.md"):
            continue
        try:
            md_doc = markdown_parser.parse_file(md_file)
            # Convert MarkdownDocument to Document
            doc = Document(
                file_path=md_doc.file_path,
                title=md_doc.title,
                sections=md_doc.sections,
                elements=md_doc.elements,
            )
            documents.append(doc)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md_file, e)

    # Build index
    warnings = index.build_from_documents(documents)
    for warning in warnings:
        logger.warning("Index: %s", warning)


def _get_section_end_line(
    section: Section,
    file_path: Path,
    file_handler: FileSystemHandler,
) -> int:
    """Get the end line of a section.

    Args:
        section: The section to get end line for
        file_path: Path to the file containing the section
        file_handler: File handler for reading files

    Returns:
        The end line number (1-based)
    """
    if section.source_location.end_line is not None:
        return section.source_location.end_line

    # Fallback: read file to get total lines
    try:
        content = file_handler.read_file(file_path)
        return len(content.splitlines())
    except FileReadError:
        return section.source_location.line + 10  # Last resort fallback
