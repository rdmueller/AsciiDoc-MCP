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

from mcp_server.models import Document, Element, Section

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
    """In-memory index for fast document structure lookups.

    This class builds and maintains an index of document structure
    from parsed AsciiDoc and Markdown documents. It provides fast
    lookups by path, level, and element type.

    Attributes:
        _path_to_section: Mapping of hierarchical path to Section
        _level_to_sections: Mapping of level to list of Sections
        _elements: List of all elements
        _type_to_elements: Mapping of element type to list of Elements
        _section_to_elements: Mapping of section path to list of Elements
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

        Currently searches section titles. Future versions may search
        full content.

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
                # Calculate simple relevance score based on match position
                match_pos = title.find(search_query)
                score = 1.0 - (match_pos / max(len(title), 1)) * 0.5

                results.append(
                    SearchResult(
                        path=path,
                        line=section.source_location.line,
                        context=section.title,
                        score=score,
                    )
                )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:max_results]

    def clear(self) -> None:
        """Clear the index."""
        self._path_to_section.clear()
        self._level_to_sections.clear()
        self._elements.clear()
        self._type_to_elements.clear()
        self._section_to_elements.clear()
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

        # Index children recursively
        for child in section.children:
            child_warnings = self._index_section(child)
            warnings.extend(child_warnings)

        return warnings

    def _index_element(self, element: Element) -> None:
        """Index an element.

        Args:
            element: Element to index
        """
        # Add to all elements list
        self._elements.append(element)

        # Index by type
        if element.type not in self._type_to_elements:
            self._type_to_elements[element.type] = []
        self._type_to_elements[element.type].append(element)

        # Index by parent section
        if element.parent_section not in self._section_to_elements:
            self._section_to_elements[element.parent_section] = []
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
