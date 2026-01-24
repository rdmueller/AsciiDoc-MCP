"""Content service for section updates.

Provides shared logic for CLI and MCP content manipulation operations.
"""

import hashlib
from pathlib import Path

from dacli.file_handler import FileReadError, FileSystemHandler, FileWriteError
from dacli.structure_index import StructureIndex


def compute_hash(content: str) -> str:
    """Compute MD5 hash (first 8 chars) for optimistic locking.

    Args:
        content: The content to hash.

    Returns:
        First 8 characters of MD5 hex digest.
    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:8]


def _get_section_end_line(
    section, file_path: Path, file_handler: FileSystemHandler
) -> int:
    """Get the end line of a section.

    If the section has an end_line in source_location, use that.
    Otherwise, calculate based on next section or file length.

    Args:
        section: The section object.
        file_path: Path to the file.
        file_handler: File system handler.

    Returns:
        The line number where the section ends.
    """
    # Use end_line if available
    if section.source_location.end_line is not None:
        return section.source_location.end_line

    # Fallback: read file and calculate
    try:
        content = file_handler.read_file(file_path)
        total_lines = len(content.splitlines())
        return total_lines
    except FileReadError:
        return section.source_location.line


def update_section(
    index: StructureIndex,
    file_handler: FileSystemHandler,
    path: str,
    content: str,
    preserve_title: bool = True,
    expected_hash: str | None = None,
) -> dict:
    """Update the content of a section.

    Args:
        index: The structure index.
        file_handler: File system handler for I/O.
        path: Hierarchical path to the section.
        content: New section content.
        preserve_title: Whether to preserve the original section title.
        expected_hash: Optional hash for optimistic locking.

    Returns:
        Dictionary with:
        - success: True if update succeeded
        - path: The normalized section path
        - location: dict with file and line
        - previous_hash: Hash before update
        - new_hash: Hash after update

        Or error dict if failed:
        - success: False
        - error: Error message
        - current_hash: (optional) Current hash if conflict
    """
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
        previous_hash = compute_hash(current_content)
    except FileReadError:
        previous_hash = ""

    # Check for conflict if expected_hash is provided
    if expected_hash is not None and expected_hash != previous_hash:
        return {
            "success": False,
            "error": (
                f"Hash conflict: expected '{expected_hash}', "
                f"but current is '{previous_hash}'"
            ),
            "current_hash": previous_hash,
        }

    # Prepare content
    new_content = content
    if preserve_title:
        stripped_content = new_content.lstrip()
        has_explicit_title = (
            stripped_content.startswith("=") or stripped_content.startswith("#")
        )

        # If content has a heading, strip it (we always use the original title)
        if has_explicit_title:
            content_lines = stripped_content.split("\n", 1)
            if len(content_lines) > 1:
                # Keep content after heading, strip leading newlines
                new_content = content_lines[1].lstrip("\n")
            else:
                new_content = ""  # Content was just the heading

        # Always prepend the original title when preserve_title is True
        file_ext = file_path.suffix.lower()
        if file_ext in (".adoc", ".asciidoc"):
            # AsciiDoc: level 0 = "=", level 1 = "==", etc.
            level_markers = "=" * (section.level + 1)
        else:
            # Markdown: level 1 = "#", level 2 = "##", etc.
            level_markers = "#" * section.level
        new_content = f"{level_markers} {section.title}\n\n{new_content}"

    # Ensure content ends with newline
    if not new_content.endswith("\n"):
        new_content += "\n"

    # Compute new hash
    new_hash = compute_hash(new_content)

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
            "previous_hash": previous_hash,
            "new_hash": new_hash,
        }
    except FileWriteError as e:
        return {"success": False, "error": str(e)}
