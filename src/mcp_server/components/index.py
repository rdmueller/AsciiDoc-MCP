from typing import Dict, List
from mcp_server.models.document import Document, Section

class DocumentIndex:
    """
    An in-memory index for parsed documents, allowing retrieval of sections by path.
    """
    def __init__(self):
        self._sections: Dict[str, Section] = {}
        self._documents: Dict[str, Document] = {}

    def _generate_section_path(self, section: Section, parent_path: str = "") -> str:
        """Generates a canonical path for a section (e.g., 'level-1-title/level-2-title')."""
        slug = section.title.lower().replace(' ', '-')
        if parent_path:
            return f"{parent_path}/{slug}"
        return slug

    def add_document(self, document: Document):
        """
        Adds all sections from a parsed Document to the index.
        """
        self._documents[document.filepath] = document

        def _add_sections_recursive(sections: List[Section], parent_path: str = ""):
            for section in sections:
                current_path = self._generate_section_path(section, parent_path)
                self._sections[current_path] = section
                _add_sections_recursive(section.subsections, current_path)

        _add_sections_recursive(document.sections)

    def get_section_by_path(self, path: str) -> Section | None:
        """
        Retrieves a section from the index by its canonical path.
        """
        return self._sections.get(path)

    def get_document_by_path(self, filepath: str) -> Document | None:
        """
        Retrieves a full Document object from the index by its filepath.
        """
        return self._documents.get(filepath)

    def get_all_top_level_sections(self) -> List[Section]:
        """
        Returns a list of all top-level sections from all indexed documents.
        """
        all_top_sections: List[Section] = []
        for doc in self._documents.values():
            all_top_sections.extend(doc.sections)
        return all_top_sections

    def search_sections(self, query: str) -> List[Section]:
        """
        Searches for sections whose title or content contains the query string.
        """
        matching_sections: List[Section] = []
        query_lower = query.lower()

        for section in self._sections.values():
            # Check title
            if query_lower in section.title.lower():
                matching_sections.append(section)
                continue # Avoid checking content if title already matches
            
            # Check content
            for line in section.content:
                if query_lower in line.lower():
                    matching_sections.append(section)
                    break # Found in content, move to next section
        return matching_sections
