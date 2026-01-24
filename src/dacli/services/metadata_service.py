"""Metadata service for project and section metadata.

Provides shared logic for CLI and MCP metadata operations.
"""

from datetime import UTC, datetime

from dacli.structure_index import StructureIndex


def get_project_metadata(index: StructureIndex) -> dict:
    """Get project-level metadata.

    Args:
        index: The structure index to query.

    Returns:
        Dictionary with:
        - path: None (indicates project-level)
        - total_files: Number of documentation files
        - total_sections: Total section count
        - total_words: Approximate word count
        - last_modified: ISO timestamp of most recent change
        - formats: List of document formats (asciidoc, markdown)
    """
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


def get_section_metadata(index: StructureIndex, path: str) -> dict:
    """Get section-level metadata.

    Args:
        index: The structure index to query.
        path: Hierarchical path to the section.

    Returns:
        Dictionary with:
        - path: The normalized section path
        - title: Section title
        - file: Source file path
        - word_count: Word count in section
        - last_modified: ISO timestamp of file modification
        - subsection_count: Number of direct children

        Or error dict if section not found:
        - error: Error message
    """
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
