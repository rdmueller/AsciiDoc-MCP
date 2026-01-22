"""Navigation API router.

Provides endpoints for navigating the document structure:
- GET /structure - Get hierarchical document structure
- GET /section/{path} - Get a specific section
- GET /sections - Get sections at a specific level
"""

from fastapi import APIRouter, HTTPException, Path, Query

from dacli.api.models import (
    ErrorDetail,
    ErrorResponse,
    LocationResponse,
    SectionDetailResponse,
    SectionResponse,
    SectionsAtLevelResponse,
    SectionSummary,
    StructureResponse,
)
from dacli.structure_index import StructureIndex

router = APIRouter(prefix="/api/v1", tags=["Navigation"])

# Global index reference - will be set by create_app
_index: StructureIndex | None = None


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


@router.get(
    "/structure",
    response_model=StructureResponse,
    summary="Get document structure",
    description="Returns the hierarchical document structure.",
)
def get_structure(
    max_depth: int | None = Query(
        default=None,
        description="Maximum depth of returned structure. None for unlimited.",
        ge=1,
    ),
) -> StructureResponse:
    """Get the hierarchical document structure."""
    index = get_index()
    structure = index.get_structure(max_depth=max_depth)

    sections = [_section_dict_to_response(s) for s in structure["sections"]]

    return StructureResponse(
        sections=sections,
        total_sections=structure["total_sections"],
    )


@router.get(
    "/section/{path:path}",
    response_model=SectionDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Section not found"},
    },
    summary="Get section by path",
    description="Returns a specific section by its hierarchical path.",
)
def get_section(
    path: str = Path(description="Hierarchical path to the section"),
) -> SectionDetailResponse:
    """Get a specific section by path."""
    index = get_index()

    # Normalize path - ensure it starts with /
    normalized_path = f"/{path}" if not path.startswith("/") else path

    section = index.get_section(normalized_path)

    if section is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PATH_NOT_FOUND",
                    "message": f"Section '{normalized_path}' not found",
                    "details": {
                        "requested_path": normalized_path,
                    },
                }
            },
        )

    # Determine format from file extension
    file_path = str(section.source_location.file)
    if file_path.endswith(".md"):
        format_type = "markdown"
    else:
        format_type = "asciidoc"

    return SectionDetailResponse(
        path=section.path,
        title=section.title,
        level=section.level,
        location=LocationResponse(
            file=file_path,
            line=section.source_location.line,
            end_line=section.source_location.end_line,
        ),
        format=format_type,
    )


@router.get(
    "/sections",
    response_model=SectionsAtLevelResponse,
    summary="Get sections at level",
    description="Returns all sections at a specific nesting level.",
)
def get_sections(
    level: int = Query(
        description="Nesting level (1 = chapter, 2 = section, etc.)",
        ge=1,
    ),
) -> SectionsAtLevelResponse:
    """Get all sections at a specific level."""
    index = get_index()

    sections = index.get_sections_at_level(level)

    section_summaries = [
        SectionSummary(path=s.path, title=s.title) for s in sections
    ]

    return SectionsAtLevelResponse(
        level=level,
        sections=section_summaries,
        count=len(section_summaries),
    )


def _section_dict_to_response(section_dict: dict) -> SectionResponse:
    """Convert a section dictionary from index to response model."""
    children = [_section_dict_to_response(c) for c in section_dict.get("children", [])]

    return SectionResponse(
        path=section_dict["path"],
        title=section_dict["title"],
        level=section_dict["level"],
        location=LocationResponse(
            file=section_dict["location"]["file"],
            line=section_dict["location"]["line"],
            end_line=section_dict["location"].get("end_line"),
        ),
        children=children,
    )
