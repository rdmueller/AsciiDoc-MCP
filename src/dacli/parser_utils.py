"""Shared utility functions for document parsers.

This module contains common functionality used by both the AsciiDoc
and Markdown parsers, following the DRY principle.
"""

import re

from dacli.models import Section


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to convert

    Returns:
        Lowercase slug with spaces/underscores replaced by dashes,
        multiple dashes collapsed, and leading/trailing dashes trimmed.
        Unicode characters are preserved.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Übersicht")
        'übersicht'
        >>> slugify("hello_world")
        'hello-world'
    """
    # Remove special characters but preserve Unicode word characters
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    # Convert spaces and underscores to dashes
    slug = re.sub(r"[\s_]+", "-", slug)
    # Collapse multiple dashes
    slug = re.sub(r"-+", "-", slug)
    # Trim leading/trailing dashes
    return slug.strip("-")


def collect_all_sections(sections: list[Section], result: list[Section]) -> None:
    """Recursively collect all sections into a flat list.

    Args:
        sections: List of sections to process
        result: List to append sections to (modified in place)

    Example:
        >>> all_sections = []
        >>> collect_all_sections(doc.sections, all_sections)
    """
    for section in sections:
        result.append(section)
        collect_all_sections(section.children, result)


def find_section_by_path(sections: list[Section], path: str) -> Section | None:
    """Recursively find a section by path.

    Args:
        sections: List of sections to search
        path: Section path to find (e.g., "introduction.goals")

    Returns:
        The section if found, None otherwise
    """
    for section in sections:
        if section.path == path:
            return section
        # Search in children
        found = find_section_by_path(section.children, path)
        if found:
            return found
    return None
