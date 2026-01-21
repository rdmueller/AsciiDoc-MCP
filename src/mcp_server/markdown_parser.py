"""Markdown Parser for GitHub Flavored Markdown documents.

This module provides parsing capabilities for GFM documents as specified in
04_markdown_parser.adoc. It extracts document structure (headings), elements
(code blocks, tables, images), and YAML frontmatter.

Key differences from AsciiDoc parser:
- No include directives - folder hierarchy defines document structure
- YAML frontmatter for metadata
- ATX-style headings only (# to ######)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp_server.models import Element, Section, SourceLocation

# Regex patterns from spec
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$")


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Lowercase, hyphenated slug
    """
    # Remove special characters, replace spaces with hyphens
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


@dataclass
class MarkdownDocument:
    """A parsed Markdown document.

    Attributes:
        file_path: Path to the source file
        title: Document title (from first H1 or frontmatter)
        frontmatter: YAML frontmatter metadata
        sections: Hierarchical list of sections
        elements: Extractable elements (code, tables, images)
    """

    file_path: Path
    title: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)


@dataclass
class FolderDocument:
    """A document composed of multiple Markdown files in a folder.

    Attributes:
        root_path: Path to the root folder
        documents: List of parsed Markdown documents (sorted)
        structure: Combined hierarchical structure
    """

    root_path: Path
    documents: list[MarkdownDocument] = field(default_factory=list)
    structure: list[Section] = field(default_factory=list)


class MarkdownParser:
    """Parser for GitHub Flavored Markdown documents.

    Parses single files or entire folder hierarchies into structured
    documents with sections and extractable elements.
    """

    def parse_file(self, file_path: Path) -> MarkdownDocument:
        """Parse a single Markdown file.

        Args:
            file_path: Path to the Markdown file

        Returns:
            Parsed MarkdownDocument

        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file has invalid encoding
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Parse sections (headings)
        sections, title = self._parse_sections(lines, file_path)

        return MarkdownDocument(
            file_path=file_path,
            title=title,
            frontmatter={},
            sections=sections,
            elements=[],
        )

    def parse_folder(self, folder_path: Path) -> FolderDocument:
        """Parse a folder with Markdown files.

        Args:
            folder_path: Path to the folder

        Returns:
            FolderDocument with all parsed files
        """
        # TODO: Implement folder parsing (AC-MD-05, AC-MD-06)
        return FolderDocument(root_path=folder_path)

    def get_section(
        self, doc: MarkdownDocument, path: str
    ) -> Section | None:
        """Find a section by its hierarchical path.

        Args:
            doc: The document to search
            path: Hierarchical path (e.g., "/chapter/section")

        Returns:
            Section if found, None otherwise
        """
        return self._find_section_by_path(doc.sections, path)

    def get_elements(
        self, doc: MarkdownDocument, element_type: str | None = None
    ) -> list[Element]:
        """Get elements from document, optionally filtered by type.

        Args:
            doc: The document to search
            element_type: Optional type filter (code, table, image)

        Returns:
            List of matching elements
        """
        if element_type is None:
            return doc.elements
        return [e for e in doc.elements if e.type == element_type]

    def _parse_sections(
        self, lines: list[str], file_path: Path
    ) -> tuple[list[Section], str]:
        """Parse headings into hierarchical sections.

        Args:
            lines: Document lines
            file_path: Source file path

        Returns:
            Tuple of (sections list, document title)
        """
        sections: list[Section] = []
        section_stack: list[Section] = []
        document_title = ""

        for line_num, line in enumerate(lines, start=1):
            match = HEADING_PATTERN.match(line)
            if not match:
                continue

            level = len(match.group(1))
            title = match.group(2).strip()

            # First H1 becomes document title
            if level == 1 and not document_title:
                document_title = title

            # Build hierarchical path
            path = self._build_path(section_stack, title, level)

            section = Section(
                title=title,
                level=level,
                path=path,
                source_location=SourceLocation(file=file_path, line=line_num),
                children=[],
            )

            # Find parent section based on level
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()

            if section_stack:
                section_stack[-1].children.append(section)
            else:
                sections.append(section)

            section_stack.append(section)

        return sections, document_title

    def _build_path(
        self, section_stack: list[Section], title: str, level: int
    ) -> str:
        """Build hierarchical path for a section.

        Args:
            section_stack: Current section stack
            title: Section title
            level: Heading level

        Returns:
            Hierarchical path string
        """
        slug = slugify(title)

        # Find ancestors at lower levels
        ancestors = []
        for s in section_stack:
            if s.level < level:
                ancestors.append(s)

        if ancestors:
            parent_path = ancestors[-1].path
            return f"{parent_path}/{slug}"
        else:
            return f"/{slug}"

    def _find_section_by_path(
        self, sections: list[Section], path: str
    ) -> Section | None:
        """Recursively find a section by path.

        Args:
            sections: Sections to search
            path: Path to find

        Returns:
            Section if found, None otherwise
        """
        for section in sections:
            if section.path == path:
                return section
            found = self._find_section_by_path(section.children, path)
            if found:
                return found
        return None
