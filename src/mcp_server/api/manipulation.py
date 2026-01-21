"""Manipulation API router.

Provides endpoints for modifying document content:
- PUT /section/{path} - Update a section's content
- POST /section/{path}/insert - Insert content relative to a section
"""

from fastapi import APIRouter, HTTPException, Path

from mcp_server.api.models import (
    ErrorDetail,
    ErrorResponse,
    InsertContentRequest,
    InsertContentResponse,
    LocationResponse,
    UpdateSectionRequest,
    UpdateSectionResponse,
)
from mcp_server.file_handler import FileReadError, FileSystemHandler, FileWriteError
from mcp_server.structure_index import StructureIndex

router = APIRouter(prefix="/api/v1", tags=["Manipulation"])

# Global index reference - will be set by create_app
_index: StructureIndex | None = None

# File handler for atomic operations
_file_handler: FileSystemHandler = FileSystemHandler()


def set_index(index: StructureIndex) -> None:
    """Set the global structure index."""
    global _index
    _index = index


def get_index() -> StructureIndex:
    """Get the global structure index."""
    if _index is None:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INDEX_NOT_READY",
                    message="Server index is not initialized",
                )
            ).model_dump(),
        )
    return _index


def _find_section_end_line(index: StructureIndex, section_path: str) -> int:
    """Find the end line of a section's direct content.

    Since SourceLocation only has a start line, we estimate the end line by:
    1. Finding the next section's (child or sibling) start line - 1, giving us
       the end of this section's direct content
    2. Or using a reasonable default if no later section exists

    This is a simplified implementation - proper end_line tracking
    should be added to the parser (see tech-debt).
    """
    section = index.get_section(section_path)
    if section is None:
        return -1

    start_line = section.source_location.line
    file_path = section.source_location.file

    # Find all sections in the same file, sorted by line number
    all_sections = []
    for path, sec in index.get_sections_by_file(file_path):
        all_sections.append((sec.source_location.line, path))

    all_sections.sort()

    # Find the section after this one
    for i, (line, path) in enumerate(all_sections):
        if path == section_path:
            if i + 1 < len(all_sections):
                # Next section starts at this line, our section ends before
                return all_sections[i + 1][0] - 1
            else:
                # This is the last section, read to end of file
                try:
                    content = _file_handler.read_file(file_path)
                    return len(content.splitlines())
                except FileReadError:
                    return start_line + 10  # Fallback

    return start_line + 10  # Fallback


@router.put(
    "/section/{path:path}",
    response_model=UpdateSectionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Section not found"},
        500: {"model": ErrorResponse, "description": "Write operation failed"},
    },
    summary="Update section content",
    description="Updates the content of a specific section.",
)
def update_section(
    path: str = Path(description="Hierarchical path to the section"),
    request: UpdateSectionRequest = ...,
) -> UpdateSectionResponse:
    """Update a section's content."""
    index = get_index()

    # Normalize path
    normalized_path = f"/{path}" if not path.startswith("/") else path

    # Find the section
    section = index.get_section(normalized_path)
    if section is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                }
            },
        )

    file_path = section.source_location.file
    start_line = section.source_location.line
    end_line = _find_section_end_line(index, normalized_path)

    # Prepare content
    new_content = request.content
    if request.preserve_title:
        stripped_content = new_content.lstrip()
        has_explicit_title = stripped_content.startswith("=") or stripped_content.startswith("#")
        if not has_explicit_title:
            # Prepend the original title line
            level_markers = "=" * (section.level + 1)
            new_content = f"{level_markers} {section.title}\n\n{new_content}"

    # Ensure content ends with newline
    if not new_content.endswith("\n"):
        new_content += "\n"

    # Perform atomic update
    try:
        _file_handler.update_section(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
            new_content=new_content,
        )
    except FileWriteError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "WRITE_FAILED",
                    "message": "Failed to write changes to file",
                    "details": {
                        "file": str(file_path),
                        "reason": str(e),
                    },
                }
            },
        )

    return UpdateSectionResponse(
        success=True,
        path=normalized_path,
        location=LocationResponse(
            file=str(file_path),
            line=start_line,
        ),
    )


@router.post(
    "/section/{path:path}/insert",
    response_model=InsertContentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid position"},
        404: {"model": ErrorResponse, "description": "Section not found"},
        500: {"model": ErrorResponse, "description": "Write operation failed"},
    },
    summary="Insert content relative to section",
    description="Inserts content before, after, or appended to a section.",
)
def insert_content(
    path: str = Path(description="Hierarchical path to the reference section"),
    request: InsertContentRequest = ...,
) -> InsertContentResponse:
    """Insert content relative to a section."""
    index = get_index()

    # Normalize path
    normalized_path = f"/{path}" if not path.startswith("/") else path

    # Find the section
    section = index.get_section(normalized_path)
    if section is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                }
            },
        )

    file_path = section.source_location.file
    start_line = section.source_location.line
    end_line = _find_section_end_line(index, normalized_path)

    # Determine insert position
    content = request.content
    if not content.endswith("\n"):
        content += "\n"

    try:
        file_content = _file_handler.read_file(file_path)
        lines = file_content.splitlines(keepends=True)

        if request.position == "before":
            # Insert before the section starts
            insert_line = start_line
            new_lines = (
                lines[: start_line - 1]
                + [content]
                + lines[start_line - 1 :]
            )
        elif request.position == "after":
            # Insert after the section ends
            insert_line = end_line + 1
            new_lines = (
                lines[:end_line]
                + [content]
                + lines[end_line:]
            )
        else:  # append
            # Append content at end of section (before the last line/children)
            insert_line = end_line
            new_lines = (
                lines[: end_line - 1]
                + [content]
                + lines[end_line - 1 :]
            )

        new_file_content = "".join(new_lines)
        _file_handler.write_file(file_path, new_file_content)

    except FileReadError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "READ_FAILED",
                    "message": f"Failed to read file: {e}",
                }
            },
        )
    except FileWriteError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "WRITE_FAILED",
                    "message": "Failed to write changes to file",
                    "details": {
                        "file": str(file_path),
                        "reason": str(e),
                    },
                }
            },
        )

    return InsertContentResponse(
        success=True,
        inserted_at=LocationResponse(
            file=str(file_path),
            line=insert_line,
        ),
    )
