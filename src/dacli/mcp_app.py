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

import hashlib
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from fastmcp import FastMCP

from dacli import __version__
from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.file_handler import FileReadError, FileSystemHandler, FileWriteError
from dacli.file_utils import find_doc_files
from dacli.markdown_parser import MarkdownStructureParser
from dacli.models import Document, Section
from dacli.structure_index import StructureIndex

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
        name="dacli",
        version=__version__,
    )

    # Initialize components
    index = StructureIndex()
    file_handler = FileSystemHandler()
    asciidoc_parser = AsciidocStructureParser(base_path=docs_root)
    markdown_parser = MarkdownStructureParser()

    # Build initial index
    _build_index(docs_root, index, asciidoc_parser, markdown_parser)

    def rebuild_index() -> None:
        """Rebuild the index after file modifications.

        This ensures the index reflects the current state of the file system
        after write operations like update_section or insert_content.
        """
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

        def build_preview(elem) -> str | None:
            """Build preview string from element attributes.

            Formats preview according to element type:
            - plantuml: [plantuml, name, format]
            - code: [source, language]
            - image: image::target[alt]
            - table: |===
            - admonition: TYPE: content (truncated)
            - list: list_type list
            """
            attrs = elem.attributes
            if elem.type == "plantuml":
                parts = ["plantuml"]
                if attrs.get("name"):
                    parts.append(attrs["name"])
                if attrs.get("format"):
                    parts.append(attrs["format"])
                return f"[{', '.join(parts)}]"
            elif elem.type == "code":
                lang = attrs.get("language", "")
                return f"[source, {lang}]" if lang else "[source]"
            elif elem.type == "image":
                target = attrs.get("target", "")
                alt = attrs.get("alt", "")
                return f"image::{target}[{alt}]"
            elif elem.type == "table":
                return "|==="
            elif elem.type == "admonition":
                atype = attrs.get("admonition_type", "NOTE")
                full_content = attrs.get("content", "")
                if len(full_content) > 30:
                    return f"{atype}: {full_content[:30]}..."
                return f"{atype}: {full_content}"
            elif elem.type == "list":
                list_type = attrs.get("list_type", "unordered")
                return f"{list_type} list"
            return None

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
                    "preview": build_preview(e),
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
        # The index uses paths without leading slash
        normalized_path = path.lstrip("/")

        section = index.get_section(normalized_path)
        if section is None:
            return {"success": False, "error": f"Section '{normalized_path}' not found"}

        file_path = section.source_location.file
        start_line = section.source_location.line
        end_line = _get_section_end_line(section, file_path, file_handler)

        # Read current content and compute hash for optimistic locking
        try:
            file_content = file_handler.read_file(file_path)
            lines = file_content.splitlines(keepends=True)
            current_content = "".join(lines[start_line - 1 : end_line])
            previous_hash = hashlib.md5(current_content.encode("utf-8")).hexdigest()[:8]
        except FileReadError:
            previous_hash = ""
            current_content = ""

        # Check for conflict if expected_hash is provided
        if expected_hash is not None and expected_hash != previous_hash:
            return {
                "success": False,
                "error": (
                    f"Hash conflict: expected '{expected_hash}', but current is '{previous_hash}'"
                ),
                "current_hash": previous_hash,
            }

        # Prepare content
        new_content = content
        if preserve_title:
            stripped_content = new_content.lstrip()
            has_explicit_title = stripped_content.startswith("=") or stripped_content.startswith(
                "#"
            )
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

        # Compute new hash
        new_hash = hashlib.md5(new_content.encode("utf-8")).hexdigest()[:8]

        # Perform update
        try:
            file_handler.update_section(
                path=file_path,
                start_line=start_line,
                end_line=end_line,
                new_content=new_content,
            )
            # Rebuild index to reflect file changes
            rebuild_index()
            return {
                "success": True,
                "path": normalized_path,
                "location": {
                    "file": str(file_path),
                    "line": start_line,
                },
                "previous_hash": previous_hash,
                "new_hash": new_hash,
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
            # Compute hash of file before modification
            previous_hash = hashlib.md5(file_content.encode("utf-8")).hexdigest()[:8]

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
            new_hash = hashlib.md5(new_file_content.encode("utf-8")).hexdigest()[:8]

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
            # Project-level metadata
            stats = index.stats()
            files = set(index._file_to_sections.keys())

            # Calculate total words from all section content
            total_words = 0
            for content in index._section_content.values():
                total_words += len(content.split())

            # Find latest modification time
            last_modified = None
            for file_path in files:
                if file_path.exists():
                    mtime = file_path.stat().st_mtime
                    if last_modified is None or mtime > last_modified:
                        last_modified = mtime

            # Detect formats from file extensions
            formats = set()
            for file_path in files:
                ext = file_path.suffix.lower()
                if ext == ".adoc":
                    formats.add("asciidoc")
                elif ext == ".md":
                    formats.add("markdown")

            return {
                "path": None,
                "total_files": len(files),
                "total_sections": stats["total_sections"],
                "total_words": total_words,
                "last_modified": (
                    datetime.fromtimestamp(last_modified, tz=UTC).isoformat()
                    if last_modified
                    else None
                ),
                "formats": sorted(formats),
            }
        else:
            # Section-level metadata
            normalized_path = path.lstrip("/")
            section = index.get_section(normalized_path)

            if section is None:
                return {"error": f"Section '{normalized_path}' not found"}

            # Get word count from section content
            content = index._section_content.get(normalized_path, "")
            word_count = len(content.split())

            # Get file modification time
            file_path = section.source_location.file
            last_modified = None
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                last_modified = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

            # Count subsections
            subsection_count = len(section.children)

            return {
                "path": normalized_path,
                "title": section.title,
                "file": str(file_path),
                "word_count": word_count,
                "last_modified": last_modified,
                "subsection_count": subsection_count,
            }

    @mcp.tool()
    def validate_structure() -> dict:
        """Validate the document structure.

        Use this tool to check the documentation for structural issues
        like unresolved includes, circular includes, or orphaned files.

        Returns:
            'valid': True if no errors, False otherwise.
            'errors': List of error objects (unresolved_include, circular_include).
            'warnings': List of warning objects (orphaned_file).
            'validation_time_ms': Time taken for validation in milliseconds.
        """
        start_time = time.time()

        errors: list[dict] = []
        warnings: list[dict] = []

        # Get all indexed files
        indexed_files = set(index._file_to_sections.keys())

        # Get all doc files in docs_root (respecting gitignore)
        all_doc_files: set[Path] = set()
        for adoc_file in find_doc_files(docs_root, "*.adoc"):
            all_doc_files.add(adoc_file.resolve())
        for md_file in find_doc_files(docs_root, "*.md"):
            if md_file.name not in ("CLAUDE.md", "README.md"):
                all_doc_files.add(md_file.resolve())

        # Check for orphaned files (files not indexed)
        indexed_resolved = {f.resolve() for f in indexed_files}
        for doc_file in all_doc_files:
            if doc_file not in indexed_resolved:
                rel_path = doc_file.relative_to(docs_root)
                warnings.append(
                    {
                        "type": "orphaned_file",
                        "path": str(rel_path),
                        "message": "File is not included in any document",
                    }
                )

        # Calculate validation time
        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_time_ms": elapsed_ms,
        }

    return mcp


def _build_index(
    docs_root: Path,
    index: StructureIndex,
    asciidoc_parser: AsciidocStructureParser,
    markdown_parser: MarkdownStructureParser,
) -> None:
    """Build the structure index from documents in docs_root.

    Args:
        docs_root: Root directory containing documentation
        index: StructureIndex to populate
        asciidoc_parser: Parser for AsciiDoc files
        markdown_parser: Parser for Markdown files
    """
    documents: list[Document] = []

    # Find and parse AsciiDoc files (respecting gitignore)
    for adoc_file in find_doc_files(docs_root, "*.adoc"):
        try:
            doc = asciidoc_parser.parse_file(adoc_file)
            documents.append(doc)
        except Exception as e:
            # Log but continue with other files
            logger.warning("Failed to parse %s: %s", adoc_file, e)

    # Find and parse Markdown files (respecting gitignore)
    for md_file in find_doc_files(docs_root, "*.md"):
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
