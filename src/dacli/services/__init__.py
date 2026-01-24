"""Service layer for dacli business logic.

This module provides shared services used by both CLI and MCP interfaces.
Services accept dependencies (index, file_handler) and return dict results.
"""

from dacli.services.content_service import compute_hash, update_section
from dacli.services.metadata_service import get_project_metadata, get_section_metadata
from dacli.services.validation_service import validate_structure

__all__ = [
    "get_project_metadata",
    "get_section_metadata",
    "validate_structure",
    "update_section",
    "compute_hash",
]
