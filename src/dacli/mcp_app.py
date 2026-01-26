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
    - get_metadata: Get project or section metadata
"""

import logging
import sys
from pathlib import Path

from fastmcp import FastMCP

from dacli import __version__
from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.file_handler import FileReadError, FileSystemHandler, FileWriteError
from dacli.file_utils import find_doc_files
from dacli.markdown_parser import MarkdownStructureParser
from dacli.models import Document
from dacli.services import (
    compute_hash,
    get_project_metadata,
    get_section_metadata,
)
from dacli.services import (
    update_section as service_update_section,
)
from dacli.services import (
    validate_structure as service_validate_structure,
)
from dacli.services.content_service import _get_section_end_line
from dacli.structure_index import StructureIndex

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_mcp_server(
    docs_root: Path | str | None = None,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        docs_root: Root directory containing documentation files.
                   If None, uses current directory.
        respect_gitignore: If True, exclude files matching .gitignore patterns.
        include_hidden: If True, include files in hidden directories.

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
        name="dacli",
        version=__version__,
    )

    # Initialize components
    index = StructureIndex()
    file_handler = FileSystemHandler()
    asciidoc_parser = AsciidocStructureParser(base_path=docs_root)
    markdown_parser = MarkdownStructureParser()

    # Build initial index
    _build_index(
        docs_root,
        index,
        asciidoc_parser,
        markdown_parser,
        respect_gitignore=respect_gitignore,
        include_hidden=include_hidden,
    )

    def rebuild_index() -> None:
        """Rebuild the index after file modifications.

        This ensures the index reflects the current state of the file system
        after write operations like update_section or insert_content.
        """
        _build_index(
            docs_root,
            index,
            asciidoc_parser,
            markdown_parser,
            respect_gitignore=respect_gitignore,
            include_hidden=include_hidden,
        )

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
            suggestions = index.get_suggestions(normalized_path)
            return {
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                    "details": {
                        "requested_path": normalized_path,
                        "suggestions": suggestions,
                    },
                }
            }

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
        max_results: int = 20,
    ) -> dict:
        """Search for content in the documentation.

        Use this tool to find sections matching a search query.
        Currently searches section titles.

        Args:
            query: Search query string (case-insensitive by default).
            scope: Optional path prefix to limit search scope
                   (e.g., '/architecture' to search only in that section).
            max_results: Maximum number of results to return (default: 20).

        Returns:
            Search results with 'query', 'results' (list of matches with
            path, line, context, score), and 'total_results'.

        Raises:
            ValueError: If query is empty or whitespace-only.
        """
        # Validate query is not empty
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

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
        recursive: bool = False,
        include_content: bool = False,
        content_limit: int | None = None,
    ) -> dict:
        """Get elements (code blocks, tables, images) from the documentation.

        Use this tool to find specific types of content elements within
        the documentation, such as code examples, tables, or diagrams.

        Args:
            element_type: Filter by type - 'code', 'table', 'image',
                          'diagram', 'list'. None returns all elements.
            section_path: Filter by section path (e.g., '/architecture').
            recursive: If True, include elements from child sections.
                       If False (default), only exact section matches.
            include_content: If True, include element content and attributes (Issue #159).
                             If False (default), only return metadata.
            content_limit: Limit content to first N lines (requires include_content=True).

        Returns:
            Dictionary with 'elements' (list of elements with type, location, and
            optionally attributes/content) and 'count'.
        """
        elements = index.get_elements(
            element_type=element_type,
            section_path=section_path,
            recursive=recursive,
        )

        # Build element dicts with optional content (Issue #159)
        element_dicts = []
        for e in elements:
            elem_dict = {
                "type": e.type,
                "parent_section": e.parent_section,
                "location": {
                    "file": str(e.source_location.file),
                    "start_line": e.source_location.line,
                    "end_line": e.source_location.end_line,
                },
            }

            # Include attributes if requested (Issue #159)
            if include_content:
                attributes = dict(e.attributes)  # Copy attributes

                # Apply content limit if specified
                if content_limit is not None and "content" in attributes:
                    content = attributes["content"]
                    lines = content.split("\n")
                    if len(lines) > content_limit:
                        attributes["content"] = "\n".join(lines[:content_limit])

                elem_dict["attributes"] = attributes

            element_dicts.append(elem_dict)

        return {
            "elements": element_dicts,
            "count": len(element_dicts),
        }

    @mcp.tool()
    def update_section(
        path: str,
        content: str,
        preserve_title: bool = True,
        expected_hash: str | None = None,
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
            expected_hash: Optional hash for optimistic locking. If provided,
                          the update will fail if the current content hash
                          doesn't match (indicating a conflicting modification).

        Returns:
            Success status with 'success', 'path', 'location', 'previous_hash',
            and 'new_hash' for optimistic locking support.
        """
        result = service_update_section(
            index=index,
            file_handler=file_handler,
            path=path,
            content=content,
            preserve_title=preserve_title,
            expected_hash=expected_hash,
        )
        # Rebuild index to reflect file changes if update was successful
        if result.get("success", False):
            rebuild_index()
        return result

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
            # Compute hash of file before modification
            previous_hash = compute_hash(file_content)

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
            # Compute hash of file after modification
            new_hash = compute_hash(new_file_content)

            file_handler.write_file(file_path, new_file_content)

            # Rebuild index to reflect file changes
            rebuild_index()

            return {
                "success": True,
                "inserted_at": {
                    "file": str(file_path),
                    "line": insert_line,
                },
                "previous_hash": previous_hash,
                "new_hash": new_hash,
            }
        except (FileReadError, FileWriteError) as e:
            return {"success": False, "error": f"Failed to insert content: {e}"}

    @mcp.tool()
    def get_metadata(path: str | None = None) -> dict:
        """Get metadata about the project or a specific section.

        Use this tool to retrieve statistics and metadata. Without a path,
        returns project-level metadata. With a path, returns section-level
        metadata including word count and file information.

        Args:
            path: Optional hierarchical path to a section. If None, returns
                  project-level metadata.

        Returns:
            For project: 'path' (null), 'total_files', 'total_sections',
            'total_words', 'last_modified', 'formats'.
            For section: 'path', 'title', 'file', 'word_count',
            'last_modified', 'subsection_count'.
        """
        if path is None:
            return get_project_metadata(index)
        else:
            return get_section_metadata(index, path)

    @mcp.tool()
    def validate_structure() -> dict:
        """Validate the document structure.

        Use this tool to check the documentation for structural issues
        like unresolved includes, circular includes, orphaned files,
        or malformed content (unclosed code blocks, tables).

        Returns:
            'valid': True if no errors, False otherwise.
            'errors': List of error objects (unresolved_include, circular_include).
            'warnings': List of warning objects (orphaned_file, unclosed_block, unclosed_table).
            'validation_time_ms': Time taken for validation in milliseconds.
        """
        return service_validate_structure(index, docs_root)

    return mcp


def _build_index(
    docs_root: Path,
    index: StructureIndex,
    asciidoc_parser: AsciidocStructureParser,
    markdown_parser: MarkdownStructureParser,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> None:
    """Build the structure index from documents in docs_root.

    Args:
        docs_root: Root directory containing documentation
        index: StructureIndex to populate
        asciidoc_parser: Parser for AsciiDoc files
        markdown_parser: Parser for Markdown files
        respect_gitignore: If True, exclude files matching .gitignore patterns
        include_hidden: If True, include files in hidden directories
    """
    documents: list[Document] = []

    # Find and parse AsciiDoc files
    for adoc_file in find_doc_files(
        docs_root, "*.adoc", respect_gitignore=respect_gitignore, include_hidden=include_hidden
    ):
        try:
            doc = asciidoc_parser.parse_file(adoc_file)
            documents.append(doc)
        except Exception as e:
            # Log but continue with other files
            logger.warning("Failed to parse %s: %s", adoc_file, e)

    # Find and parse Markdown files
    for md_file in find_doc_files(
        docs_root, "*.md", respect_gitignore=respect_gitignore, include_hidden=include_hidden
    ):
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


