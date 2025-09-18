from typing import Dict, List
from mcp_server.models.document import Document, Section

class DocumentIndex:
    """
    An in-memory index for parsed documents, allowing retrieval of sections by path.
    """
    def __init__(self):
        self._sections: Dict[str, Section] = {}

    def _generate_section_path(self, section: Section) -> str:
        """Generates a canonical path for a section (e.g., 'level-1-title')."""
        # For now, just use the title, lowercased and hyphenated
        return section.title.lower().replace(' ', '-')

    def add_document(self, document: Document):
        """
        Adds all sections from a parsed Document to the index.
        """
        def _add_sections_recursive(sections: List[Section]):
            for section in sections:
                path = self._generate_section_path(section)
                self._sections[path] = section
                _add_sections_recursive(section.subsections)

        _add_sections_recursive(document.sections)

    def get_section_by_path(self, path: str) -> Section | None:
        """
        Retrieves a section from the index by its canonical path.
        """
        return self._sections.get(path)
