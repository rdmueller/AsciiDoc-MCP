"""File System Handler for atomic read/write operations.

Implements ADR-004: Atomic Writes via Temporary Files.

This module provides safe file operations with:
- UTF-8 encoding with proper error handling
- Atomic writes using backup-and-replace strategy
- Line-based operations for section updates
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class FileReadError(Exception):
    """Error during file read operation.

    Raised for:
    - File not found
    - Permission denied
    - Encoding errors
    """

    pass


class FileWriteError(Exception):
    """Error during file write operation.

    Raised for:
    - Permission denied
    - Disk full
    - Atomic operation failures
    """

    pass


class FileSystemHandler:
    """Handler for atomic file system operations.

    Implements ADR-004 backup-and-replace strategy for atomic writes:
    1. Create backup of original file (.bak)
    2. Write changes to temporary file (.tmp)
    3. Atomically rename temp file to original
    4. Delete backup file
    5. On failure: restore from backup, cleanup temp files

    Note: This class is not thread-safe for concurrent access to the
    same file. Use external locking if concurrent access is needed.
    """

    def read_file(self, path: Path | str) -> str:
        """Read entire file content as UTF-8 string.

        Args:
            path: Path to the file

        Returns:
            File content as string

        Raises:
            FileReadError: If file cannot be read (not found, permissions, encoding)
        """
        path = Path(path)

        if not path.exists():
            raise FileReadError(f"File not found: {path}")

        try:
            return path.read_text(encoding="utf-8")
        except PermissionError as e:
            raise FileReadError(f"Permission denied reading file: {path}") from e
        except UnicodeDecodeError as e:
            raise FileReadError(
                f"Encoding error reading file (not valid UTF-8): {path}"
            ) from e
        except OSError as e:
            raise FileReadError(f"Error reading file {path}: {e}") from e

    def read_lines(
        self, path: Path | str, start: int, end: int
    ) -> list[str]:
        """Read specific line range from file.

        Args:
            path: Path to the file
            start: Start line number (1-based, inclusive)
            end: End line number (1-based, inclusive)

        Returns:
            List of lines including newline characters

        Raises:
            FileReadError: If file cannot be read
            ValueError: If line range is invalid
        """
        path = Path(path)

        # Validate parameters
        if start < 1:
            raise ValueError("Start line must be >= 1 (1-based indexing)")
        if end < start:
            raise ValueError(f"Start line ({start}) must be <= end line ({end})")

        # Read all lines
        content = self.read_file(path)
        lines = content.splitlines(keepends=True)

        total_lines = len(lines)
        if end > total_lines:
            raise ValueError(
                f"End line ({end}) exceeds file length ({total_lines} lines)"
            )

        # Convert to 0-based index and extract range
        return lines[start - 1 : end]

    def write_file(self, path: Path | str, content: str) -> None:
        """Write content to file atomically using backup-and-replace.

        Implements ADR-004 atomic write strategy:
        1. If file exists, create backup (.bak)
        2. Write content to temporary file (.tmp)
        3. Atomically rename temp to target
        4. Delete backup
        5. On error: restore backup, cleanup temp

        Args:
            path: Path to the file
            content: Content to write

        Raises:
            FileWriteError: If write operation fails
        """
        path = Path(path)
        backup_path = path.with_suffix(path.suffix + ".bak")
        temp_path = path.with_suffix(path.suffix + ".tmp")

        # Track what we've created for cleanup
        backup_created = False
        temp_created = False

        try:
            # Step 1: Create backup if original exists
            if path.exists():
                shutil.copy2(path, backup_path)
                backup_created = True
                logger.debug(f"Created backup: {backup_path}")

            # Step 2: Write to temporary file
            try:
                temp_path.write_text(content, encoding="utf-8")
                temp_created = True
                logger.debug(f"Wrote temp file: {temp_path}")
            except PermissionError as e:
                raise FileWriteError(
                    f"Permission denied writing to {temp_path}"
                ) from e
            except OSError as e:
                raise FileWriteError(f"Error writing temp file {temp_path}: {e}") from e

            # Step 3: Atomic rename (replace original)
            try:
                # os.replace provides atomic file replacement on POSIX and Windows
                os.replace(temp_path, path)
                temp_created = False  # temp file is now the target
                logger.debug(f"Replaced {path} with temp file")
            except OSError as e:
                raise FileWriteError(
                    f"Error during atomic replace of {path}: {e}"
                ) from e

            # Step 4: Delete backup (success path)
            if backup_created:
                try:
                    backup_path.unlink()
                    backup_created = False
                    logger.debug(f"Deleted backup: {backup_path}")
                except OSError as e:
                    # Non-fatal: backup remains but operation succeeded
                    logger.warning(f"Could not delete backup {backup_path}: {e}")

        except FileWriteError:
            # Re-raise FileWriteError after cleanup
            self._cleanup_on_error(
                path, backup_path, temp_path, backup_created, temp_created
            )
            raise
        except Exception as e:
            # Unexpected error - cleanup and wrap
            self._cleanup_on_error(
                path, backup_path, temp_path, backup_created, temp_created
            )
            raise FileWriteError(f"Unexpected error writing {path}: {e}") from e

    def _cleanup_on_error(
        self,
        path: Path,
        backup_path: Path,
        temp_path: Path,
        backup_created: bool,
        temp_created: bool,
    ) -> None:
        """Cleanup after a failed write operation.

        Restores original from backup if available, removes temp files.
        """
        # Remove temp file if it exists
        if temp_created and temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_path}")
            except OSError as e:
                logger.warning(f"Could not cleanup temp file {temp_path}: {e}")

        # Restore from backup if we have one
        if backup_created and backup_path.exists():
            try:
                # If original was corrupted/deleted, restore it
                if not path.exists():
                    shutil.copy2(backup_path, path)
                    logger.debug(f"Restored {path} from backup")
                # Remove backup
                backup_path.unlink()
                logger.debug(f"Cleaned up backup: {backup_path}")
            except OSError as e:
                logger.warning(f"Could not restore from backup {backup_path}: {e}")

    def update_section(
        self,
        path: Path | str,
        start_line: int,
        end_line: int,
        new_content: str,
    ) -> None:
        """Update a line range in a file atomically.

        Replaces lines from start_line to end_line (inclusive, 1-based)
        with new_content.

        Args:
            path: Path to the file
            start_line: First line to replace (1-based)
            end_line: Last line to replace (1-based, inclusive)
            new_content: Content to insert (should include newlines)

        Raises:
            FileReadError: If file cannot be read
            FileWriteError: If file cannot be written
            ValueError: If line range is invalid
        """
        path = Path(path)

        # Validate parameters
        if start_line < 1:
            raise ValueError("Start line must be >= 1 (1-based indexing)")
        if end_line < start_line:
            raise ValueError(f"Start line ({start_line}) must be <= end line ({end_line})")

        # Read current content
        content = self.read_file(path)
        lines = content.splitlines(keepends=True)

        # Handle file without trailing newline
        if content and not content.endswith("\n") and lines:
            lines[-1] = lines[-1] + "\n"

        total_lines = len(lines)
        if end_line > total_lines:
            raise ValueError(
                f"End line ({end_line}) exceeds file length ({total_lines} lines)"
            )

        # Build new content:
        # - Lines before start_line
        # - New content
        # - Lines after end_line
        new_lines = (
            lines[: start_line - 1]  # Lines before (0-indexed)
            + [new_content]  # New content (should include newlines)
            + lines[end_line:]  # Lines after (0-indexed, end_line is exclusive)
        )

        # Join and write
        new_file_content = "".join(new_lines)
        self.write_file(path, new_file_content)
