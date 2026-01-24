"""Validation service for document structure validation.

Provides shared logic for CLI and MCP validation operations.
"""

import time
from pathlib import Path

from dacli.file_utils import find_doc_files
from dacli.structure_index import StructureIndex


def validate_structure(index: StructureIndex, docs_root: Path) -> dict:
    """Validate the document structure.

    Checks for:
    - Orphaned files (not included in any document)
    - Parse warnings (unclosed blocks, tables)

    Args:
        index: The structure index to validate.
        docs_root: Root directory of documentation.

    Returns:
        Dictionary with:
        - valid: True if no errors, False otherwise
        - errors: List of error objects
        - warnings: List of warning objects
        - validation_time_ms: Time taken for validation
    """
    start_time = time.time()

    errors: list[dict] = []
    warnings: list[dict] = []

    # Get all indexed files
    indexed_files = set(index._file_to_sections.keys())

    # Get all doc files in docs_root (respecting gitignore)
    all_doc_files: set[Path] = set()
    for adoc_file in find_doc_files(docs_root, "*.adoc"):
        all_doc_files.add(adoc_file.resolve())
    for md_file in find_doc_files(docs_root, "*.md"):
        all_doc_files.add(md_file.resolve())

    # Check for orphaned files (files not indexed)
    indexed_resolved = {f.resolve() for f in indexed_files}
    docs_root_resolved = docs_root.resolve()
    for doc_file in all_doc_files:
        if doc_file not in indexed_resolved:
            try:
                rel_path = doc_file.relative_to(docs_root_resolved)
            except ValueError:
                rel_path = doc_file
            warnings.append({
                "type": "orphaned_file",
                "path": str(rel_path),
                "message": "File is not included in any document",
            })

    # Collect parse warnings from all documents (Issue #148)
    for doc in index._documents:
        for pw in doc.parse_warnings:
            try:
                rel_path = pw.file.relative_to(docs_root_resolved)
            except ValueError:
                rel_path = pw.file
            warnings.append({
                "type": pw.type.value,
                "path": f"{rel_path}:{pw.line}",
                "message": pw.message,
            })

    # Calculate validation time
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validation_time_ms": elapsed_ms,
    }
