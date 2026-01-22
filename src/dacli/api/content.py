"""Content Access API router.

Provides endpoints for searching and accessing document elements:
- POST /search - Search document content
- GET /elements - Get elements by type
"""

import time

from fastapi import APIRouter, HTTPException, Query

from dacli.api.models import (
    VALID_ELEMENT_TYPES,
    ElementItem,
    ElementLocation,
    ElementsResponse,
    ErrorDetail,
    ErrorResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from dacli.structure_index import StructureIndex

router = APIRouter(prefix="/api/v1", tags=["Content Access"])

# Global index reference - will be set by create_app
_index: StructureIndex | None = None

# Mapping from internal element types to API types
ELEMENT_TYPE_TO_API = {
    "plantuml": "diagram",
    "code": "code",
    "table": "table",
    "image": "image",
}

# Reverse mapping from API types to internal types
API_TYPE_TO_ELEMENT = {
    "diagram": ["plantuml"],  # plantuml maps to diagram
    "code": ["code"],
    "table": ["table"],
    "image": ["image"],
}


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


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search document content",
    description="Searches the documentation content and returns matching sections.",
)
def search_content(request: SearchRequest) -> SearchResponse:
    """Search for content matching the query."""
    # Validate query is not empty
    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_QUERY",
                    message="Query cannot be empty",
                )
            ).model_dump(),
        )

    index = get_index()

    # Measure search time
    start_time = time.time()

    # Perform search
    results = index.search(
        query=request.query,
        scope=request.scope,
        case_sensitive=request.case_sensitive,
        max_results=request.max_results,
    )

    # Calculate search time in milliseconds
    elapsed = time.time() - start_time
    elapsed_ms = elapsed * 1000
    if elapsed_ms <= 0:
        search_time_ms = 0
    else:
        search_time_ms = max(1, int(round(elapsed_ms)))

    # Convert to response model
    result_items = [
        SearchResultItem(
            path=r.path,
            line=r.line,
            context=r.context,
            score=r.score,
        )
        for r in results
    ]

    return SearchResponse(
        query=request.query,
        results=result_items,
        total_results=len(result_items),
        search_time_ms=search_time_ms,
    )


@router.get(
    "/elements",
    response_model=ElementsResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid element type"},
    },
    summary="Get elements by type",
    description="Returns all elements of a specific type, optionally filtered by section.",
)
def get_elements(
    type: str = Query(
        description="Element type: diagram, table, code, list, image"
    ),
    path: str | None = Query(
        default=None,
        description="Optional section path to filter elements",
    ),
) -> ElementsResponse:
    """Get elements filtered by type and optionally by section path."""
    # Validate element type
    if type not in VALID_ELEMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_TYPE",
                    message=f"Unknown element type '{type}'",
                    details={
                        "valid_types": list(VALID_ELEMENT_TYPES),
                    },
                )
            ).model_dump(),
        )

    index = get_index()

    # Get internal element types that map to this API type
    internal_types = API_TYPE_TO_ELEMENT.get(type, [])

    # Collect elements for all matching internal types
    all_elements = []
    for internal_type in internal_types:
        elements = index.get_elements(
            element_type=internal_type,
            section_path=path,
        )
        all_elements.extend(elements)

    # Track element indices per section
    section_element_counts: dict[str, int] = {}

    # Convert to response model
    element_items = []
    for elem in all_elements:
        # Get or initialize index for this section
        section_path = elem.parent_section
        if section_path not in section_element_counts:
            section_element_counts[section_path] = 0
        element_index = section_element_counts[section_path]
        section_element_counts[section_path] += 1

        # Build preview from attributes if available
        preview = None
        if elem.attributes:
            # Build preview string from first few attributes
            attr_parts = []
            for key, value in list(elem.attributes.items())[:3]:
                attr_parts.append(f"{key}={value}")
            if attr_parts:
                preview = ", ".join(attr_parts)

        element_items.append(
            ElementItem(
                type=type,  # Use API type, not internal type
                path=section_path,
                index=element_index,
                location=ElementLocation(
                    file=str(elem.source_location.file),
                    start_line=elem.source_location.line,
                    # Note: SourceLocation currently exposes only a single line field.
                    # Until an explicit end_line is available, we intentionally set
                    # end_line to the same value as start_line.
                    # TODO: Update this when SourceLocation includes an end_line range.
                    end_line=elem.source_location.line,
                ),
                preview=preview,
            )
        )

    return ElementsResponse(
        type=type,
        elements=element_items,
        count=len(element_items),
    )
