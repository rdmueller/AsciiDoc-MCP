"""File utilities for documentation scanning with gitignore support.

This module provides utilities for scanning documentation files while
respecting .gitignore patterns and filtering out hidden directories.
"""

from collections.abc import Iterator
from pathlib import Path

import pathspec


def load_gitignore_spec(docs_root: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from the docs root directory.

    Args:
        docs_root: Root directory to look for .gitignore

    Returns:
        PathSpec object for matching files, or None if no .gitignore exists
    """
    gitignore_path = docs_root / ".gitignore"

    if not gitignore_path.exists():
        return None

    try:
        with open(gitignore_path, encoding="utf-8") as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitignore", patterns)
    except (OSError, UnicodeDecodeError):
        # If we can't read the file, treat as no gitignore
        return None


def _is_hidden_path(path: Path, root: Path) -> bool:
    """Check if any component of the path (relative to root) starts with a dot.

    Args:
        path: Path to check
        root: Root directory to calculate relative path from

    Returns:
        True if any path component starts with '.'
    """
    try:
        relative = path.relative_to(root)
        return any(part.startswith(".") for part in relative.parts)
    except ValueError:
        # Path is not relative to root
        return False


def find_doc_files(
    docs_root: Path,
    pattern: str,
    *,
    respect_gitignore: bool = True,
    include_hidden: bool = False,
) -> Iterator[Path]:
    """Find documentation files matching a pattern, respecting gitignore.

    This function scans a directory recursively for files matching the given
    pattern (e.g., "*.adoc" or "*.md") while:
    - Respecting .gitignore patterns (when respect_gitignore=True)
    - Skipping hidden directories (when include_hidden=False)

    Args:
        docs_root: Root directory to scan
        pattern: Glob pattern for files (e.g., "*.adoc", "*.md")
        respect_gitignore: If True, exclude files matching .gitignore patterns
        include_hidden: If True, include files in hidden directories

    Yields:
        Path objects for matching documentation files
    """
    # Load gitignore spec if requested
    gitignore_spec = load_gitignore_spec(docs_root) if respect_gitignore else None

    # Scan for files
    for file_path in docs_root.rglob(pattern):
        # Skip hidden directories unless explicitly included
        if not include_hidden and _is_hidden_path(file_path, docs_root):
            continue

        # Skip gitignored files
        if gitignore_spec is not None:
            try:
                relative_path = file_path.relative_to(docs_root)
                # Check both the file path and parent directories
                if _matches_gitignore(relative_path, gitignore_spec):
                    continue
            except ValueError:
                # Path is not relative to docs_root, skip gitignore check
                pass

        yield file_path


def _matches_gitignore(relative_path: Path, spec: pathspec.PathSpec) -> bool:
    """Check if a path matches gitignore patterns.

    This checks the path and all parent directories against the gitignore spec.

    Args:
        relative_path: Path relative to the docs root
        spec: PathSpec object with gitignore patterns

    Returns:
        True if the path should be ignored
    """
    path_str = str(relative_path)

    # Check the file itself
    if spec.match_file(path_str):
        return True

    # Check parent directories (for patterns like "node_modules/")
    for parent in relative_path.parents:
        if parent == Path("."):
            continue
        # Add trailing slash to match directory patterns
        dir_path = str(parent) + "/"
        if spec.match_file(dir_path):
            return True
        # Also check without trailing slash
        if spec.match_file(str(parent)):
            return True

    return False
