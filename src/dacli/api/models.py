"""Pydantic models for API responses.

These models define the JSON response structure for the Navigation API
and Content Access API as specified in 02_api_specification.adoc.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Valid element types for GET /elements endpoint
VALID_ELEMENT_TYPES = frozenset(["diagram", "table", "code", "list", "image"])


class LocationResponse(BaseModel):
    """Location of a section in a source file."""

    file: str = Field(description="Relative path to the file")
    line: int = Field(description="1-based start line number")
    end_line: int | None = Field(default=None, description="1-based end line number (inclusive)")


class SectionResponse(BaseModel):
    """Section response for structure endpoint."""

    path: str = Field(description="Hierarchical path (e.g., '/chapter-1/section-2')")
    title: str = Field(description="Section title")
    level: int = Field(description="Nesting depth (1 = chapter)")
    location: LocationResponse
    children: list["SectionResponse"] = Field(default_factory=list)


class StructureResponse(BaseModel):
    """Response for GET /structure endpoint."""

    sections: list[SectionResponse]
    total_sections: int = Field(description="Total number of sections in index")


class SectionDetailResponse(BaseModel):
    """Detailed section response for GET /section/{path}."""

    path: str
    title: str
    level: int
    location: LocationResponse
    format: str = Field(description="Document format: 'asciidoc' or 'markdown'")


class SectionSummary(BaseModel):
    """Summary of a section (without children)."""

    path: str
    title: str


class SectionsAtLevelResponse(BaseModel):
    """Response for GET /sections endpoint."""

    level: int
    sections: list[SectionSummary]
    count: int


class ErrorDetail(BaseModel):
    """Error detail in error response."""

    code: str = Field(description="Error code (e.g., 'PATH_NOT_FOUND')")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional details")


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: ErrorDetail


# ============================================================================
# Content Access API Models
# ============================================================================


class SearchRequest(BaseModel):
    """Request body for POST /search endpoint."""

    query: str = Field(min_length=1, description="Search query string")
    scope: str | None = Field(default=None, description="Restrict search to path prefix")
    case_sensitive: bool = Field(default=False, description="Case-sensitive search")
    max_results: int = Field(default=20, ge=1, le=1000, description="Maximum results (default: 20)")


class SearchResultItem(BaseModel):
    """A single search result."""

    path: str = Field(description="Section path where match was found")
    line: int = Field(description="Line number of the match")
    context: str = Field(description="Context text around the match")
    score: float = Field(ge=0, le=1, description="Relevance score (0-1)")


class SearchResponse(BaseModel):
    """Response for POST /search endpoint."""

    query: str = Field(description="The search query that was executed")
    results: list[SearchResultItem]
    total_results: int = Field(description="Total number of matches found")
    search_time_ms: int = Field(description="Search execution time in milliseconds")


class ElementLocation(BaseModel):
    """Location of an element with line range."""

    file: str = Field(description="Relative path to the file")
    start_line: int = Field(description="1-based starting line number")
    end_line: int = Field(description="1-based ending line number (inclusive)")


class ElementItem(BaseModel):
    """A single element in the response."""

    type: str = Field(description="Element type (diagram, table, code, list, image)")
    path: str = Field(description="Section path containing this element")
    index: int = Field(description="Index of element within its section")
    location: ElementLocation
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Element-specific attributes and content (Issue #159)",
    )
    # Note: preview field removed in Issue #142 as redundant


class ElementsResponse(BaseModel):
    """Response for GET /elements endpoint."""

    type: str = Field(description="Requested element type")
    elements: list[ElementItem]
    count: int = Field(description="Number of elements returned")


# ============================================================================
# Manipulation API Models
# ============================================================================


class UpdateSectionRequest(BaseModel):
    """Request body for PUT /section/{path} endpoint."""

    content: str = Field(description="New section content")
    preserve_title: bool = Field(
        default=True,
        description="Keep original title if content doesn't include one",
    )


class UpdateSectionResponse(BaseModel):
    """Response for PUT /section/{path} endpoint."""

    success: bool = Field(default=True)
    path: str = Field(description="Section path that was updated")
    location: LocationResponse


class InsertContentRequest(BaseModel):
    """Request body for POST /section/{path}/insert endpoint."""

    position: Literal["before", "after", "append"] = Field(
        description="Insert position: 'before', 'after', or 'append'"
    )
    content: str = Field(description="Content to insert")


class InsertContentResponse(BaseModel):
    """Response for POST /section/{path}/insert endpoint."""

    success: bool = Field(default=True)
    inserted_at: LocationResponse


# Allow forward references
SectionResponse.model_rebuild()
