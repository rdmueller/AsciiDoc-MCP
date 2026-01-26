"""Markdown Parser for GitHub Flavored Markdown documents.

This module provides parsing capabilities for GFM documents as specified in
04_markdown_parser.adoc. It extracts document structure (headings), elements
(code blocks, tables, images), and YAML frontmatter.

Key differences from AsciiDoc parser:
- No include directives - folder hierarchy defines document structure
- YAML frontmatter for metadata
- ATX-style headings only (# to ######)
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dacli.models import Element, Section, SourceLocation
from dacli.parser_utils import (
    collect_all_sections,
    find_section_by_path,
    slugify,
)

logger = logging.getLogger(__name__)

# Regex patterns from spec
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^(`{3,}|~{3,})([a-zA-Z0-9_+-]*)?\s*$")
TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|[\s:|-]+\|$")
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")

# List patterns
UNORDERED_LIST_PATTERN = re.compile(r"^[\s]*[-*+]\s+.+$")
ORDERED_LIST_PATTERN = re.compile(r"^[\s]*\d+\.\s+.+$")

# Setext heading patterns (for warning detection - not supported)
# H1: line of text followed by line of ='s (at least 3)
SETEXT_H1_UNDERLINE = re.compile(r"^={3,}\s*$")
# H2: line of text followed by line of -'s (at least 3)
SETEXT_H2_UNDERLINE = re.compile(r"^-{3,}\s*$")


@dataclass
class MarkdownDocument:
    """A parsed Markdown document.

    Attributes:
        file_path: Path to the source file
        title: Document title (from first H1 or frontmatter)
        frontmatter: YAML frontmatter metadata
        sections: Hierarchical list of sections
        elements: Extractable elements (code, tables, images)
    """

    file_path: Path
    title: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)


@dataclass
class FolderDocument:
    """A document composed of multiple Markdown files in a folder.

    Attributes:
        root_path: Path to the root folder
        documents: List of parsed Markdown documents (sorted)
        structure: Combined hierarchical structure from all documents.
            NOTE: This field is not yet implemented and will always be empty.
            Future implementation will merge section hierarchies from all
            documents into a unified structure respecting folder boundaries.
    """

    root_path: Path
    documents: list[MarkdownDocument] = field(default_factory=list)
    structure: list[Section] = field(default_factory=list)


class MarkdownStructureParser:
    """Parser for GitHub Flavored Markdown documents.

    Parses single files or entire folder hierarchies into structured
    documents with sections and extractable elements.

    Attributes:
        base_path: Optional base path for calculating relative file prefixes.
                   If not provided, file paths are relative to the file's parent.
    """

    def __init__(self, base_path: Path | None = None):
        """Initialize the parser.

        Args:
            base_path: Optional base path for resolving relative file paths.
                       If not provided, file prefixes will be just the filename stem.
        """
        self.base_path = base_path

    def _get_file_prefix(self, file_path: Path) -> str:
        """Calculate file prefix for path generation (Issue #130, ADR-008).

        The file prefix is the relative path from base_path to file_path,
        without the file extension. This ensures unique paths across documents.

        Args:
            file_path: Path to the document being parsed

        Returns:
            Relative path without extension (e.g., "guides/installation")
        """
        if self.base_path is not None:
            try:
                relative = file_path.relative_to(self.base_path)
            except ValueError:
                # file_path is not relative to base_path, use just the stem
                relative = Path(file_path.stem)
        else:
            # No base_path provided, use just the stem
            relative = Path(file_path.stem)
        # Remove extension and convert to forward slashes
        return str(relative.with_suffix("")).replace("\\", "/")

    def parse_file(self, file_path: Path) -> MarkdownDocument:
        """Parse a single Markdown file.

        Args:
            file_path: Path to the Markdown file

        Returns:
            Parsed MarkdownDocument

        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file has invalid encoding
        """
        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter first
        frontmatter, content_without_frontmatter = self._parse_frontmatter(content)

        lines = content_without_frontmatter.splitlines()

        # Calculate line offset from frontmatter
        frontmatter_lines = len(content.splitlines()) - len(lines)

        # Parse sections (headings)
        sections, heading_title = self._parse_sections(
            lines, file_path, line_offset=frontmatter_lines
        )

        # Calculate end_line for all sections
        total_lines = len(content.splitlines())
        self._compute_end_lines(sections, file_path, total_lines)

        # Parse elements (code blocks, tables, images)
        elements = self._parse_elements(
            lines, file_path, sections, line_offset=frontmatter_lines
        )

        # Title priority: frontmatter > first H1 > empty
        title = frontmatter.get("title", heading_title)

        return MarkdownDocument(
            file_path=file_path,
            title=title,
            frontmatter=frontmatter,
            sections=sections,
            elements=elements,
        )

    def parse_folder(self, folder_path: Path) -> FolderDocument:
        """Parse a folder with Markdown files.

        Args:
            folder_path: Path to the folder

        Returns:
            FolderDocument with all parsed files

        Raises:
            FileNotFoundError: If the folder path does not exist
            NotADirectoryError: If the path is not a directory
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        if not folder_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        documents: list[MarkdownDocument] = []

        # Collect all markdown files recursively
        md_files = self._collect_markdown_files(folder_path)

        # Sort files according to spec rules
        sorted_files = self._sort_files(md_files, folder_path)

        # Parse each file
        for file_path in sorted_files:
            try:
                doc = self.parse_file(file_path)
                documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        return FolderDocument(
            root_path=folder_path,
            documents=documents,
            structure=[],  # Not yet implemented - see class docstring
        )

    def get_section(
        self, doc: MarkdownDocument, path: str
    ) -> Section | None:
        """Find a section by its hierarchical path.

        Args:
            doc: The document to search
            path: Hierarchical path (e.g., "/chapter/section")

        Returns:
            Section if found, None otherwise
        """
        return find_section_by_path(doc.sections, path)

    def get_elements(
        self, doc: MarkdownDocument, element_type: str | None = None
    ) -> list[Element]:
        """Get elements from document, optionally filtered by type.

        Args:
            doc: The document to search
            element_type: Optional type filter (code, table, image)

        Returns:
            List of matching elements
        """
        if element_type is None:
            return doc.elements
        return [e for e in doc.elements if e.type == element_type]

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from content.

        Args:
            content: Full file content

        Returns:
            Tuple of (frontmatter dict, content without frontmatter)
        """
        # Check if content starts with frontmatter delimiter
        if not content.startswith("---"):
            return {}, content

        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        yaml_content = match.group(1)
        try:
            frontmatter = yaml.safe_load(yaml_content)
            if frontmatter is None:
                frontmatter = {}
        except yaml.YAMLError as e:
            logger.warning(f"Invalid YAML frontmatter: {e}")
            frontmatter = {}

        # Remove frontmatter from content
        content_without_frontmatter = content[match.end():]
        return frontmatter, content_without_frontmatter

    def _parse_sections(
        self, lines: list[str], file_path: Path, line_offset: int = 0
    ) -> tuple[list[Section], str]:
        """Parse headings into hierarchical sections.

        Args:
            lines: Document lines
            file_path: Source file path
            line_offset: Line offset from frontmatter

        Returns:
            Tuple of (sections list, document title)
        """
        # Calculate file prefix early for empty file handling (Issue #145)
        file_prefix = self._get_file_prefix(file_path)

        # Check if file is empty or contains only whitespace (Issue #145)
        is_empty = not lines or all(line.strip() == "" for line in lines)
        if is_empty:
            # Create minimal root section for empty files
            filename = file_path.stem  # Filename without extension
            root_section = Section(
                title=filename,
                level=0,
                path=file_prefix,
                source_location=SourceLocation(file=file_path, line=1, end_line=1),
            )
            return [root_section], filename

        sections: list[Section] = []
        section_stack: list[Section] = []
        document_title = ""
        # Track used paths for disambiguation (Issue #123)
        used_paths: dict[str, int] = {}

        def get_unique_path(base_path: str) -> str:
            """Get a unique path, appending -2, -3 etc. for duplicates."""
            if base_path not in used_paths:
                used_paths[base_path] = 1
                return base_path
            # Path already exists, disambiguate
            used_paths[base_path] += 1
            new_path = f"{base_path}-{used_paths[base_path]}"
            # Track the new path too in case there are further references
            used_paths[new_path] = 1
            return new_path

        # Track previous lines for Setext detection
        prev_line = ""
        prev_prev_line = ""

        for line_num, line in enumerate(lines, start=1 + line_offset):
            # Detect Setext headings and warn (not supported per spec)
            self._warn_setext_heading(
                line, prev_line, prev_prev_line, line_num, file_path
            )
            prev_prev_line = prev_line
            prev_line = line
            match = HEADING_PATTERN.match(line)
            if not match:
                continue

            level = len(match.group(1))
            title = match.group(2).strip()

            # First H1 becomes document title
            if level == 1 and not document_title:
                document_title = title

            # Build hierarchical path with file prefix (Issue #130, ADR-008)
            base_path = self._build_path(section_stack, title, level, file_prefix)
            # Get unique path (Issue #123: disambiguate duplicates)
            path = get_unique_path(base_path)

            section = Section(
                title=title,
                level=level,
                path=path,
                source_location=SourceLocation(file=file_path, line=line_num),
                children=[],
            )

            # Find parent section based on level
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()

            if section_stack:
                section_stack[-1].children.append(section)
            else:
                sections.append(section)

            section_stack.append(section)

        return sections, document_title

    def _warn_setext_heading(
        self,
        current_line: str,
        prev_line: str,
        prev_prev_line: str,
        line_num: int,
        file_path: Path,
    ) -> None:
        """Warn if a Setext-style heading is detected.

        Setext headings are not supported per spec. This method detects them
        and logs a warning to help users understand why their document
        structure might look incorrect.

        Args:
            current_line: Current line being processed
            prev_line: Previous line
            prev_prev_line: Line before previous (for horizontal rule check)
            line_num: Current line number (1-based)
            file_path: Source file path
        """
        # Check for Setext H1 (===)
        if SETEXT_H1_UNDERLINE.match(current_line):
            # Previous line must be non-empty text (potential heading text)
            if prev_line.strip() and not prev_line.startswith("#"):
                logger.warning(
                    f"Setext-style heading detected at {file_path}:{line_num - 1}. "
                    f"Setext headings (underlined with '===') are not supported. "
                    f"Use ATX-style headings (# Heading) instead."
                )
                return

        # Check for Setext H2 (---)
        if SETEXT_H2_UNDERLINE.match(current_line):
            # Setext H2: previous line must be non-empty text (heading text)
            # Horizontal rule: previous line is blank/empty
            # If prev_line has text, it's a Setext heading
            if prev_line.strip() and not prev_line.startswith("#"):
                logger.warning(
                    f"Setext-style heading detected at {file_path}:{line_num - 1}. "
                    f"Setext headings (underlined with '---') are not supported. "
                    f"Use ATX-style headings (## Heading) instead."
                )

    # NOTE: `file_path` is accepted for API compatibility with the AsciiDoc
    # parser but is not used by the Markdown implementation.
    def _compute_end_lines(
        self, sections: list[Section], file_path: Path, total_lines: int
    ) -> None:
        """Compute end_line for all sections.

        For each section, end_line is set to the line before the next section
        starts, or the last line of the file.

        Args:
            sections: List of parsed sections (modified in place)
            file_path: Source file path
            total_lines: Total number of lines in the file
        """
        # Collect all sections into a flat list
        all_sections: list[Section] = []
        collect_all_sections(sections, all_sections)

        if not all_sections:
            return

        # Sort by start line
        all_sections.sort(key=lambda s: s.source_location.line)

        # Compute end_line for each section
        for i, section in enumerate(all_sections):
            if i + 1 < len(all_sections):
                # Next section starts, our section ends one line before
                next_start = all_sections[i + 1].source_location.line
                section.source_location.end_line = next_start - 1
            else:
                # Last section ends at file end
                section.source_location.end_line = total_lines

    def _parse_elements(
        self,
        lines: list[str],
        file_path: Path,
        sections: list[Section],
        line_offset: int = 0,
    ) -> list[Element]:
        """Parse extractable elements from document.

        Args:
            lines: Document lines
            file_path: Source file path
            sections: Parsed sections for parent context
            line_offset: Line offset from frontmatter

        Returns:
            List of extracted elements
        """
        elements: list[Element] = []
        current_section_path = ""
        in_code_block = False
        code_fence_char = ""
        code_fence_count = 0
        code_block_start_line = 0
        code_block_language: str | None = None
        code_block_content: list[str] = []

        # Track table state
        in_table = False
        table_start_line = 0
        table_end_line = 0  # Track last table row line for end_line
        table_columns = 0
        table_rows = 0
        has_separator = False

        # Track list state
        current_list_type: str | None = None
        current_list_element: Element | None = None

        # Content tracking for Issue #159
        table_content: list[str] = []
        list_content: list[str] = []

        for line_num, line in enumerate(lines, start=1 + line_offset):
            # Track current section
            heading_match = HEADING_PATTERN.match(line)
            if heading_match and not in_code_block:
                # If we were in a table, finalize it before starting a new heading.
                if in_table:
                    if has_separator:
                        elements.append(
                            Element(
                                type="table",
                                source_location=SourceLocation(
                                    file=file_path,
                                    line=table_start_line,
                                    end_line=table_end_line,
                                ),
                                attributes={
                                    "columns": table_columns,
                                    "rows": table_rows,
                                    "content": "\n".join(table_content),  # Issue #159
                                },
                                parent_section=current_section_path,
                            )
                        )
                    # Reset table state regardless of whether it was valid
                    in_table = False
                    table_columns = 0
                    table_rows = 0
                    has_separator = False
                title = heading_match.group(2).strip()
                current_section_path = self._find_section_path(sections, title)
                continue

            # Handle code blocks
            fence_match = CODE_FENCE_PATTERN.match(line)
            if fence_match:
                fence_char = fence_match.group(1)[0]
                fence_count = len(fence_match.group(1))

                if not in_code_block:
                    # Opening fence
                    in_code_block = True
                    code_fence_char = fence_char
                    code_fence_count = fence_count
                    code_block_start_line = line_num
                    code_block_language = fence_match.group(2) or None
                    code_block_content = []
                elif fence_char == code_fence_char and fence_count >= code_fence_count:
                    # Closing fence
                    elements.append(
                        Element(
                            type="code",
                            source_location=SourceLocation(
                                file=file_path,
                                line=code_block_start_line,
                                end_line=line_num,  # Closing fence line
                            ),
                            attributes={
                                "language": code_block_language,
                                "content": "\n".join(code_block_content),
                            },
                            parent_section=current_section_path,
                        )
                    )
                    in_code_block = False
                continue

            # Collect content inside code blocks
            if in_code_block:
                code_block_content.append(line)
                continue

            # Handle tables
            table_row_match = TABLE_ROW_PATTERN.match(line)
            if table_row_match:
                table_end_line = line_num  # Update end_line for each row
                if not in_table:
                    # Start of table
                    in_table = True
                    table_start_line = line_num
                    table_content = []  # Initialize content tracking (Issue #159)
                    # Count columns from header row
                    cells = table_row_match.group(1).split("|")
                    table_columns = len(cells)
                    table_rows = 0
                    has_separator = False
                elif TABLE_SEPARATOR_PATTERN.match(line):
                    has_separator = True
                elif has_separator:
                    # Data row after separator
                    table_rows += 1
                # Collect table line (Issue #159)
                table_content.append(line)
                continue
            elif in_table:
                # End of table (non-table line)
                if has_separator:
                    elements.append(
                        Element(
                            type="table",
                            source_location=SourceLocation(
                                file=file_path,
                                line=table_start_line,
                                end_line=table_end_line,
                            ),
                            attributes={
                                "columns": table_columns,
                                "rows": table_rows,
                                "content": "\n".join(table_content),  # Issue #159
                            },
                            parent_section=current_section_path,
                        )
                    )
                in_table = False

            # Handle images
            image_match = IMAGE_PATTERN.search(line)
            if image_match:
                image_attributes = {
                    "alt": image_match.group(1),
                    "src": image_match.group(2),
                }
                title = image_match.group(3)
                if title is not None:
                    image_attributes["title"] = title

                elements.append(
                    Element(
                        type="image",
                        source_location=SourceLocation(
                            file=file_path, line=line_num, end_line=line_num
                        ),
                        attributes=image_attributes,
                        parent_section=current_section_path,
                    )
                )
                # Save list content before reset (Issue #159)
                if current_list_element is not None and list_content:
                    current_list_element.attributes["content"] = "\n".join(list_content)
                current_list_type = None  # Reset list tracking
                current_list_element = None
                continue

            # Handle lists (unordered and ordered)
            if not in_code_block and not in_table:
                # Check for unordered list (*, -, +)
                if UNORDERED_LIST_PATTERN.match(line):
                    if current_list_type != "unordered":
                        # Save previous list content if any (Issue #159)
                        if current_list_element is not None and list_content:
                            current_list_element.attributes["content"] = "\n".join(list_content)
                        current_list_type = "unordered"
                        list_content = []  # Initialize content tracking (Issue #159)
                        element = Element(
                            type="list",
                            source_location=SourceLocation(
                                file=file_path, line=line_num, end_line=line_num
                            ),
                            attributes={"list_type": "unordered"},
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_list_element = element
                    # Collect list item content (Issue #159)
                    list_content.append(line)
                    # Update end_line for each list item
                    if current_list_element is not None:
                        current_list_element.source_location.end_line = line_num
                    continue

                # Check for ordered list (1., 2., etc.)
                if ORDERED_LIST_PATTERN.match(line):
                    if current_list_type != "ordered":
                        # Save previous list content if any (Issue #159)
                        if current_list_element is not None and list_content:
                            current_list_element.attributes["content"] = "\n".join(list_content)
                        current_list_type = "ordered"
                        list_content = []  # Initialize content tracking (Issue #159)
                        element = Element(
                            type="list",
                            source_location=SourceLocation(
                                file=file_path, line=line_num, end_line=line_num
                            ),
                            attributes={"list_type": "ordered"},
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_list_element = element
                    # Collect list item content (Issue #159)
                    list_content.append(line)
                    # Update end_line for each list item
                    if current_list_element is not None:
                        current_list_element.source_location.end_line = line_num
                    continue

                # If non-empty, non-list line, reset list tracking
                if line.strip():
                    # Save list content before reset (Issue #159)
                    if current_list_element is not None and list_content:
                        current_list_element.attributes["content"] = "\n".join(list_content)
                    current_list_type = None
                    current_list_element = None

        # Handle unclosed code block at end of file
        if in_code_block:
            logger.warning(
                f"Unclosed code block at end of file {file_path} "
                f"(started at line {code_block_start_line}). "
                f"Code block will be ignored."
            )

        # Handle table at end of file
        if in_table and has_separator:
            elements.append(
                Element(
                    type="table",
                    source_location=SourceLocation(
                        file=file_path,
                        line=table_start_line,
                        end_line=table_end_line,
                    ),
                    attributes={
                        "columns": table_columns,
                        "rows": table_rows,
                        "content": "\n".join(table_content),  # Issue #159
                    },
                    parent_section=current_section_path,
                )
            )

        # Save list content if list is still open at end of file (Issue #159)
        if current_list_element is not None and list_content:
            current_list_element.attributes["content"] = "\n".join(list_content)

        return elements

    def _collect_markdown_files(self, folder_path: Path) -> list[Path]:
        """Collect all Markdown files in folder recursively.

        Args:
            folder_path: Root folder path

        Returns:
            List of Markdown file paths
        """
        md_files: list[Path] = []

        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower() == ".md":
                md_files.append(item)
            elif item.is_dir() and not item.name.startswith("."):
                md_files.extend(self._collect_markdown_files(item))

        return md_files

    def _sort_files(self, files: list[Path], root: Path) -> list[Path]:
        """Sort files according to spec rules.

        Sorting rules:
        1. index.md / README.md come first in their directory
        2. Numeric prefixes are sorted numerically (1, 2, 10 not 1, 10, 2)
        3. Files without numeric prefixes come after those with prefixes
        4. Directories are processed in order, with their contents inline

        Args:
            files: List of file paths
            root: Root folder for relative path calculation

        Returns:
            Sorted list of file paths
        """

        def sort_key(path: Path) -> tuple:
            """Generate sort key for a file path."""
            rel_path = path.relative_to(root)
            parts = rel_path.parts

            # Build sort key from path components
            key_parts: list[tuple[int, int, str]] = []
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1

                if is_last:
                    # File name - check for special names
                    name_lower = part.lower()
                    if name_lower in ("index.md", "readme.md"):
                        # Special files come first (priority 0)
                        key_parts.append((0, 0, ""))
                    else:
                        # Extract numeric prefix if present
                        num, rest = self._extract_numeric_prefix(part)
                        if num is not None:
                            # Numeric prefix (priority 1)
                            key_parts.append((1, num, rest))
                        else:
                            # No numeric prefix (priority 2)
                            key_parts.append((2, 0, part.lower()))
                else:
                    # Directory name
                    num, rest = self._extract_numeric_prefix(part)
                    if num is not None:
                        key_parts.append((1, num, rest))
                    else:
                        key_parts.append((2, 0, part.lower()))

            return tuple(key_parts)

        return sorted(files, key=sort_key)

    def _extract_numeric_prefix(self, name: str) -> tuple[int | None, str]:
        """Extract numeric prefix from filename.

        Args:
            name: Filename (e.g., "01_intro.md")

        Returns:
            Tuple of (number or None, rest of name)
        """
        match = re.match(r"^(\d+)[_-](.+)$", name)
        if match:
            return int(match.group(1)), match.group(2)
        return None, name

    def _find_section_path(self, sections: list[Section], title: str) -> str:
        """Find section path by title.

        Args:
            sections: Sections to search
            title: Title to find

        Returns:
            Section path or empty string
        """
        for section in sections:
            if section.title == title:
                return section.path
            found = self._find_section_path(section.children, title)
            if found:
                return found
        return ""

    def _build_path(
        self, section_stack: list[Section], title: str, level: int, file_prefix: str
    ) -> str:
        """Build hierarchical path for a section with file prefix (Issue #130, ADR-008).

        Args:
            section_stack: Current section stack
            title: Section title
            level: Heading level
            file_prefix: File prefix for cross-document unique paths

        Returns:
            Hierarchical path string with file prefix
            - H1 (document title): file_prefix
            - H2+: file_prefix:section_path (dot-separated hierarchy)
        """
        # H1 (document title) path is the file prefix (Issue #130, ADR-008)
        if level == 1:
            return file_prefix

        slug = slugify(title)

        # Find ancestors at lower levels
        ancestors = []
        for s in section_stack:
            if s.level < level:
                ancestors.append(s)

        if ancestors:
            parent = ancestors[-1]
            # If parent is H1 (document title), section path is just the slug
            if parent.level == 1:
                section_path = slug
            else:
                # Extract section_path from parent (part after the colon)
                if ":" in parent.path:
                    parent_section_path = parent.path.split(":", 1)[1]
                else:
                    parent_section_path = parent.path
                section_path = f"{parent_section_path}.{slug}"
        else:
            section_path = slug

        # Full path is file_prefix:section_path
        return f"{file_prefix}:{section_path}"
