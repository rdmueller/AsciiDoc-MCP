"""Structure Index for fast document lookups.

This module provides an in-memory index for fast lookups of document
structure and sections. It is built from parsed documents (AsciiDoc
or Markdown) and supports the API endpoints defined in the specification.

Key features:
- O(1) lookup by hierarchical path
- Element filtering by type and section
- Simple text search across section titles
- Statistics for health checks
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from dacli.models import Document, Element, Section

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with context.

    Attributes:
        path: Hierarchical path to the match
        line: Line number in source file
        context: Matching text/context
        score: Relevance score (0-1)
    """

    path: str
    line: int
    context: str
    score: float


class StructureIndex:
    """In-memory index for fast document structure lookups and full-text search.

    This class builds and maintains an index of document structure
    from parsed AsciiDoc and Markdown documents. It provides fast
    lookups by path, level, element type, and full-text search.

    Attributes:
        _path_to_section: Mapping of hierarchical path to Section
        _level_to_sections: Mapping of level to list of Sections
        _elements: List of all elements
        _type_to_elements: Mapping of element type to list of Elements
        _section_to_elements: Mapping of section path to list of Elements
        _file_to_sections: Mapping of file path to list of Sections
        _section_content: Mapping of section path to content for full-text search
        _documents: List of indexed documents
        _index_ready: Whether the index has been built
    """

    def __init__(self) -> None:
        """Initialize an empty index."""
        self._path_to_section: dict[str, Section] = {}
        self._level_to_sections: dict[int, list[Section]] = {}
        self._elements: list[Element] = []
        self._type_to_elements: dict[str, list[Element]] = {}
        self._section_to_elements: dict[str, list[Element]] = {}
        self._file_to_sections: dict[Path, list[Section]] = {}
        self._section_content: dict[str, str] = {}  # Content for full-text search
        self._documents: list[Document] = []
        self._top_level_sections: list[Section] = []
        self._index_ready: bool = False

    def build_from_documents(self, documents: list[Document]) -> list[str]:
        """Build index from parsed documents.

        Args:
            documents: List of parsed documents (AsciiDoc or Markdown)

        Returns:
            List of warning messages (e.g., duplicate paths)
        """
        warnings: list[str] = []

        # Clear existing index
        self.clear()

        self._documents = documents

        # Index all sections and elements from each document
        for doc in documents:
            # Index sections recursively
            for section in doc.sections:
                self._top_level_sections.append(section)
                section_warnings = self._index_section(section)
                warnings.extend(section_warnings)

            # Index elements
            for element in doc.elements:
                self._index_element(element)

        self._index_ready = True
        logger.info(
            f"Index built: {len(self._path_to_section)} sections, "
            f"{len(self._elements)} elements from {len(documents)} documents"
        )

        return warnings

    def get_structure(self, max_depth: int | None = None) -> dict:
        """Get hierarchical document structure.

        Args:
            max_depth: Maximum depth to return (None for unlimited)

        Returns:
            Dictionary with 'sections' (hierarchical tree) and 'total_sections'
        """
        if max_depth is not None:
            sections = [
                self._section_to_dict(s, max_depth, current_depth=1)
                for s in self._top_level_sections
            ]
        else:
            sections = [
                self._section_to_dict(s, max_depth=None, current_depth=1)
                for s in self._top_level_sections
            ]

        return {
            "sections": sections,
            "total_sections": len(self._path_to_section),
        }

    def get_section(self, path: str) -> Section | None:
        """Find section by hierarchical path.

        Args:
            path: Hierarchical path (e.g., "/chapter-1/section-2")

        Returns:
            Section if found, None otherwise
        """
        return self._path_to_section.get(path)

    def get_sections_at_level(self, level: int) -> list[Section]:
        """Get all sections at a specific level.

        Args:
            level: Nesting level (1 = chapter, 2 = section, etc.)

        Returns:
            List of sections at the specified level
        """
        return self._level_to_sections.get(level, [])

    def get_sections_by_file(self, file_path: Path) -> list[Section]:
        """Get all sections defined in a specific file.

        Args:
            file_path: Path to the source file

        Returns:
            List of sections in the file (empty if file not indexed)
        """
        return self._file_to_sections.get(file_path, [])

    def get_suggestions(
        self, requested_path: str, max_suggestions: int = 5
    ) -> list[str]:
        """Get path suggestions for a non-existent path.

        Finds similar paths using prefix and suffix matching.
        Useful for providing helpful suggestions in 404 error responses.

        Args:
            requested_path: The requested path that was not found
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of similar existing paths, sorted by relevance
        """
        if not requested_path:
            return []

        suggestions: list[tuple[int, str]] = []  # (score, path)

        for existing_path in self._path_to_section.keys():
            score = self._calculate_path_similarity(requested_path, existing_path)
            if score > 0:
                suggestions.append((score, existing_path))

        # Sort by score descending, then by path alphabetically
        suggestions.sort(key=lambda x: (-x[0], x[1]))

        return [path for _, path in suggestions[:max_suggestions]]

    def _calculate_path_similarity(self, requested: str, existing: str) -> int:
        """Calculate similarity score between two paths.

        Args:
            requested: The requested path
            existing: An existing path to compare

        Returns:
            Similarity score (higher = more similar), 0 = no match
        """
        requested_parts = requested.split(".")
        existing_parts = existing.split(".")
        score = 0

        # Prefix matching: paths sharing the same parent
        if len(requested_parts) > 1 and len(existing_parts) > 1:
            # Check if parent path matches
            requested_parent = ".".join(requested_parts[:-1])
            existing_parent = ".".join(existing_parts[:-1])
            if requested_parent == existing_parent:
                score += 10  # Strong match for same parent

        # Suffix matching: paths with similar last segment
        requested_last = requested_parts[-1].lower()
        existing_last = existing_parts[-1].lower()
        if requested_last == existing_last:
            score += 5  # Exact last segment match
        elif requested_last in existing_last or existing_last in requested_last:
            score += 3  # Partial last segment match

        # First segment matching (same top-level section)
        if requested_parts[0] == existing_parts[0]:
            score += 2

        return score

    def get_elements(
        self,
        element_type: str | None = None,
        section_path: str | None = None,
    ) -> list[Element]:
        """Get elements, optionally filtered by type and/or section.

        Args:
            element_type: Optional type filter (code, table, image, etc.)
            section_path: Optional section path filter

        Returns:
            List of matching elements
        """
        # Start with all elements or filtered by type
        if element_type is not None:
            elements = self._type_to_elements.get(element_type, [])
        else:
            elements = self._elements

        # Further filter by section if specified
        if section_path is not None:
            elements = [e for e in elements if e.parent_section == section_path]

        return elements

    def search(
        self,
        query: str,
        scope: str | None = None,
        case_sensitive: bool = False,
        max_results: int = 50,
    ) -> list[SearchResult]:
        """Search for content matching query.

        Searches both section titles and section content.

        Args:
            query: Search query string
            scope: Optional path prefix to limit search scope
            case_sensitive: Whether search is case-sensitive
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        results: list[SearchResult] = []

        # Prepare query for matching
        search_query = query if case_sensitive else query.lower()

        for path, section in self._path_to_section.items():
            # Check scope filter
            if scope is not None and not path.startswith(scope):
                continue

            # Check title match
            title = section.title if case_sensitive else section.title.lower()
            if search_query in title:
                # Calculate simple relevance score - title matches score higher
                match_pos = title.find(search_query)
                score = 1.0 - (match_pos / max(len(title), 1)) * 0.3

                results.append(
                    SearchResult(
                        path=path,
                        line=section.source_location.line,
                        context=section.title,
                        score=score,
                    )
                )
                continue  # Don't also search content if title matched

            # Check content match
            content = self._section_content.get(path, "")
            search_content = content if case_sensitive else content.lower()
            if search_query in search_content:
                # Find match position and create context snippet
                match_pos = search_content.find(search_query)
                context = self._build_context_snippet(content, match_pos, query)

                # Content matches score lower than title matches
                score = 0.7 - (match_pos / max(len(content), 1)) * 0.2

                # Find the line number of the match
                line = section.source_location.line
                lines_before_match = content[:match_pos].count("\n")
                line += lines_before_match

                results.append(
                    SearchResult(
                        path=path,
                        line=line,
                        context=context,
                        score=score,
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:max_results]

    def _build_context_snippet(
        self, content: str, match_pos: int, query: str, context_chars: int = 40
    ) -> str:
        """Build a context snippet around the match position.

        Args:
            content: Full content text
            match_pos: Position of the match
            query: The search query
            context_chars: Number of characters to show before/after match

        Returns:
            Context snippet with ellipsis if truncated
        """
        start = max(0, match_pos - context_chars)
        end = min(len(content), match_pos + len(query) + context_chars)

        snippet = content[start:end]

        # Clean up whitespace and add ellipsis
        snippet = " ".join(snippet.split())
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def clear(self) -> None:
        """Clear the index."""
        self._path_to_section.clear()
        self._level_to_sections.clear()
        self._elements.clear()
        self._type_to_elements.clear()
        self._section_to_elements.clear()
        self._file_to_sections.clear()
        self._section_content.clear()
        self._documents.clear()
        self._top_level_sections.clear()
        self._index_ready = False

    def stats(self) -> dict:
        """Return index statistics.

        Returns:
            Dictionary with index statistics for health checks
        """
        return {
            "total_sections": len(self._path_to_section),
            "total_elements": len(self._elements),
            "total_documents": len(self._documents),
            "sections_with_content": len(self._section_content),
            "index_ready": self._index_ready,
            "sections_by_level": {
                level: len(sections)
                for level, sections in self._level_to_sections.items()
            },
            "elements_by_type": {
                etype: len(elements)
                for etype, elements in self._type_to_elements.items()
            },
        }

    def _index_section(self, section: Section) -> list[str]:
        """Index a section and its children recursively.

        Args:
            section: Section to index

        Returns:
            List of warning messages
        """
        warnings: list[str] = []

        # Check for duplicate path
        if section.path in self._path_to_section:
            warnings.append(
                f"Duplicate section path: '{section.path}' "
                f"(first at {self._path_to_section[section.path].source_location.file}:"
                f"{self._path_to_section[section.path].source_location.line}, "
                f"duplicate at {section.source_location.file}:{section.source_location.line})"
            )
            # Reject the duplicate - do not add to any index
            # Still index children recursively in case they have unique paths
            for child in section.children:
                child_warnings = self._index_section(child)
                warnings.extend(child_warnings)
            return warnings

        # Index by path
        self._path_to_section[section.path] = section

        # Index by level
        if section.level not in self._level_to_sections:
            self._level_to_sections[section.level] = []
        self._level_to_sections[section.level].append(section)

        # Index by file
        file_path = section.source_location.file
        if file_path not in self._file_to_sections:
            self._file_to_sections[file_path] = []
        self._file_to_sections[file_path].append(section)

        # Read and store section content for full-text search
        self._store_section_content(section)

        # Index children recursively
        for child in section.children:
            child_warnings = self._index_section(child)
            warnings.extend(child_warnings)

        return warnings

    def _store_section_content(self, section: Section) -> None:
        """Read and store section content for full-text search.

        Args:
            section: Section to read content for
        """
        try:
            file_path = section.source_location.file
            if not file_path.exists():
                return

            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            start_line = section.source_location.line - 1  # Convert to 0-based
            end_line = section.source_location.end_line
            if end_line is None:
                end_line = len(lines)

            section_content = "\n".join(lines[start_line:end_line])
            self._section_content[section.path] = section_content
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read content for section '%s': %s", section.path, e)

    def _index_element(self, element: Element) -> None:
        """Index an element.

        Args:
            element: Element to index
        """
        # Assign index within parent section (0-based)
        if element.parent_section not in self._section_to_elements:
            self._section_to_elements[element.parent_section] = []
        element.index = len(self._section_to_elements[element.parent_section])

        # Add to all elements list
        self._elements.append(element)

        # Index by type
        if element.type not in self._type_to_elements:
            self._type_to_elements[element.type] = []
        self._type_to_elements[element.type].append(element)

        # Index by parent section
        self._section_to_elements[element.parent_section].append(element)

    def _section_to_dict(
        self,
        section: Section,
        max_depth: int | None,
        current_depth: int,
    ) -> dict:
        """Convert a section to a dictionary for API response.

        Args:
            section: Section to convert
            max_depth: Maximum depth to include children
            current_depth: Current depth in the tree

        Returns:
            Dictionary representation of the section
        """
        result = {
            "path": section.path,
            "title": section.title,
            "level": section.level,
            "location": {
                "file": str(section.source_location.file),
                "line": section.source_location.line,
                "end_line": section.source_location.end_line,
            },
        }

        # Include children based on max_depth
        if max_depth is None or current_depth < max_depth:
            result["children"] = [
                self._section_to_dict(child, max_depth, current_depth + 1)
                for child in section.children
            ]
        else:
            result["children"] = []

        return result
