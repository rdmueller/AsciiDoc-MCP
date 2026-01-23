"""AsciiDoc Parser for MCP Documentation Server.

This module provides the AsciidocStructureParser class for parsing AsciiDoc documents.
It supports section extraction (AC-ADOC-01), attributes (AC-ADOC-02),
includes (AC-ADOC-03, AC-ADOC-04), structural elements (AC-ADOC-05,
AC-ADOC-06, AC-ADOC-07), and cross-references (AC-ADOC-08).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from dacli.models import (
    CrossReference,
    Document,
    Element,
    Section,
    SourceLocation,
)

# Regex patterns from specification
SECTION_PATTERN = re.compile(r"^(={1,6})\s+(.+?)(?:\s+=*)?$")
ATTRIBUTE_PATTERN = re.compile(r"^:([a-zA-Z0-9_-]+):\s*(.*)$")
INCLUDE_PATTERN = re.compile(r"^include::(.+?)\[(.*)\]$")

# Element patterns - with optional whitespace after commas
CODE_BLOCK_START_PATTERN = re.compile(r"^\[source(?:,\s*([a-zA-Z0-9_+-]+))?\]$")
PLANTUML_BLOCK_START_PATTERN = re.compile(
    r"^\[plantuml(?:,\s*([a-zA-Z0-9_-]+))?(?:,\s*([a-zA-Z0-9_]+))?\]$"
)
# Mermaid and Ditaa diagram patterns (Issue #122)
MERMAID_BLOCK_START_PATTERN = re.compile(
    r"^\[mermaid(?:,\s*([a-zA-Z0-9_-]+))?(?:,\s*([a-zA-Z0-9_]+))?\]$"
)
DITAA_BLOCK_START_PATTERN = re.compile(
    r"^\[ditaa(?:,\s*([a-zA-Z0-9_-]+))?(?:,\s*([a-zA-Z0-9_]+))?\]$"
)
LISTING_DELIMITER_PATTERN = re.compile(r"^-{4,}$")
TABLE_DELIMITER_PATTERN = re.compile(r"^\|===$")
IMAGE_PATTERN = re.compile(r"^image::(.+?)\[(.*)?\]$")
ADMONITION_PATTERN = re.compile(r"^(NOTE|TIP|IMPORTANT|WARNING|CAUTION):\s*(.*)$")

# Cross-reference pattern: <<target>> or <<target,display text>>
XREF_PATTERN = re.compile(r"<<([^,>]+)(?:,([^>]+))?>>", re.MULTILINE)

# List patterns
UNORDERED_LIST_PATTERN = re.compile(r"^\*+\s+.+$")
ORDERED_LIST_PATTERN = re.compile(r"^\.+\s+.+$")
DESCRIPTION_LIST_PATTERN = re.compile(r"^.+::(\s+.+)?$")


class CircularIncludeError(Exception):
    """Raised when a circular include is detected."""

    def __init__(self, file_path: Path, include_chain: list[Path]):
        """Initialize the error.

        Args:
            file_path: The file that caused the circular reference
            include_chain: The chain of includes that led to the cycle
        """
        self.file_path = file_path
        self.include_chain = include_chain
        chain_str = " -> ".join(str(p.name) for p in include_chain)
        super().__init__(f"Circular include detected: {chain_str} -> {file_path.name}")


def _title_to_slug(title: str) -> str:
    """Convert a section title to a URL-friendly slug.

    Args:
        title: The section title

    Returns:
        A lowercase slug with spaces replaced by dashes
    """
    # Remove special characters, convert to lowercase, replace spaces with dashes
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


@dataclass
class IncludeInfo:
    """Information about a resolved include directive.

    Attributes:
        source_location: Where the include directive was found
        target_path: The resolved path to the included file
        options: Include options (leveloffset, lines, etc.)
    """

    source_location: SourceLocation
    target_path: Path
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class AsciidocDocument(Document):
    """A parsed AsciiDoc document.

    Extends Document with AsciiDoc-specific fields.

    Attributes:
        attributes: Document attributes (:attr: value)
        cross_references: List of cross-references found
        includes: List of resolved includes
    """

    attributes: dict[str, str] = field(default_factory=dict)
    cross_references: list[CrossReference] = field(default_factory=list)
    includes: list[IncludeInfo] = field(default_factory=list)


class AsciidocStructureParser:
    """Parser for AsciiDoc documents.

    Parses AsciiDoc files and extracts structure, elements, cross-references,
    and includes, providing the full AsciiDoc parsing functionality required
    by the MCP documentation server (including section extraction
    as defined in AC-ADOC-01).

    Attributes:
        base_path: Base path for resolving relative file paths
        max_include_depth: Maximum depth for nested includes (default: 20)
    """

    def __init__(self, base_path: Path, max_include_depth: int = 20):
        """Initialize the parser.

        Args:
            base_path: Base path for resolving relative file paths
            max_include_depth: Maximum depth for nested includes
        """
        self.base_path = base_path
        self.max_include_depth = max_include_depth

    def _get_file_prefix(self, file_path: Path) -> str:
        """Calculate file prefix for path generation (Issue #130, ADR-008).

        The file prefix is the relative path from base_path to file_path,
        without the file extension. This ensures unique paths across documents.

        Args:
            file_path: Path to the document being parsed

        Returns:
            Relative path without extension (e.g., "guides/installation")
        """
        try:
            relative = file_path.relative_to(self.base_path)
        except ValueError:
            # file_path is not relative to base_path, use just the stem
            relative = Path(file_path.stem)
        # Remove extension and convert to forward slashes
        return str(relative.with_suffix("")).replace("\\", "/")

    def get_section(
        self, doc: AsciidocDocument, path: str
    ) -> Section | None:
        """Get a section by its hierarchical path.

        Args:
            doc: The parsed document
            path: Dot-separated section path (e.g., "haupttitel.kapitel-1")

        Returns:
            The section if found, None otherwise
        """
        return self._find_section_by_path(doc.sections, path)

    def _find_section_by_path(
        self, sections: list[Section], path: str
    ) -> Section | None:
        """Recursively find a section by path.

        Args:
            sections: List of sections to search
            path: Section path to find

        Returns:
            The section if found, None otherwise
        """
        for section in sections:
            if section.path == path:
                return section
            # Search in children
            result = self._find_section_by_path(section.children, path)
            if result:
                return result
        return None

    def get_elements(
        self, doc: AsciidocDocument, element_type: str | None = None
    ) -> list[Element]:
        """Get elements from a document, optionally filtered by type.

        Args:
            doc: The parsed document
            element_type: Optional type to filter by (code, table, image, etc.)

        Returns:
            List of elements matching the criteria
        """
        if element_type is None:
            return doc.elements
        return [e for e in doc.elements if e.type == element_type]

    def parse_file(
        self,
        file_path: Path,
        _depth: int = 0,
        _include_chain: list[Path] | None = None,
    ) -> AsciidocDocument:
        """Parse an AsciiDoc file.

        Args:
            file_path: Path to the AsciiDoc file
            _depth: Internal parameter for tracking include depth
            _include_chain: Internal parameter for tracking include chain

        Returns:
            Parsed AsciidocDocument

        Raises:
            FileNotFoundError: If the file does not exist
            CircularIncludeError: If a circular include is detected
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Initialize or copy include chain
        if _include_chain is None:
            _include_chain = []

        # Check for circular include
        resolved_path = file_path.resolve()
        if resolved_path in [p.resolve() for p in _include_chain]:
            raise CircularIncludeError(file_path, _include_chain)

        # Add current file to include chain
        current_chain = _include_chain + [file_path]

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Parse attributes first (they can be used in sections)
        attributes = self._parse_attributes(lines)

        # Expand includes and collect include info
        expanded_lines, includes = self._expand_includes(
            lines, file_path, _depth, current_chain
        )

        # Parse sections with attribute substitution
        sections, title = self._parse_sections(
            expanded_lines, file_path, attributes
        )

        # Calculate end_line for all sections
        self._compute_end_lines(sections, expanded_lines)

        # Parse elements with section context
        elements = self._parse_elements(expanded_lines, sections, attributes)

        # Parse cross-references
        cross_references = self._parse_cross_references(expanded_lines)

        return AsciidocDocument(
            file_path=file_path,
            title=title,
            sections=sections,
            elements=elements,
            attributes=attributes,
            cross_references=cross_references,
            includes=includes,
        )

    def _expand_includes(
        self,
        lines: list[str],
        file_path: Path,
        depth: int,
        include_chain: list[Path],
    ) -> tuple[list[tuple[str, Path, int, SourceLocation | None]], list[IncludeInfo]]:
        """Expand include directives in lines.

        Args:
            lines: Document lines
            file_path: Path to the source file
            depth: Current include depth
            include_chain: Chain of files for circular include detection

        Returns:
            Tuple of (expanded lines with source info, list of IncludeInfo)

        Raises:
            CircularIncludeError: If a circular include is detected
        """
        expanded: list[tuple[str, Path, int, SourceLocation | None]] = []
        includes: list[IncludeInfo] = []

        for line_num, line in enumerate(lines, start=1):
            match = INCLUDE_PATTERN.match(line)
            if match and depth < self.max_include_depth:
                include_path = match.group(1)
                options_str = match.group(2)

                # Parse options
                options: dict[str, str] = {}
                if options_str:
                    for opt in options_str.split(","):
                        if "=" in opt:
                            key, value = opt.split("=", 1)
                            options[key.strip()] = value.strip()

                # Resolve include path relative to current file
                target_path = (file_path.parent / include_path).resolve()

                # Check for circular include
                if target_path in [p.resolve() for p in include_chain]:
                    raise CircularIncludeError(target_path, include_chain)

                # Record include info
                include_info = IncludeInfo(
                    source_location=SourceLocation(file=file_path, line=line_num),
                    target_path=target_path,
                    options=options,
                )
                includes.append(include_info)

                # Expand the included file
                if target_path.exists():
                    included_content = target_path.read_text(encoding="utf-8")
                    included_lines = included_content.splitlines()

                    # Create resolved_from reference
                    resolved_from = SourceLocation(file=file_path, line=line_num)

                    # Recursively expand includes in the included file
                    new_chain = include_chain + [target_path]
                    nested_expanded, nested_includes = self._expand_includes(
                        included_lines, target_path, depth + 1, new_chain
                    )
                    includes.extend(nested_includes)

                    # Add expanded lines with resolved_from info
                    for inc_line, inc_file, inc_line_num, inc_resolved in nested_expanded:
                        # Preserve original resolved_from or use current include location
                        final_resolved = inc_resolved if inc_resolved else resolved_from
                        expanded.append((inc_line, inc_file, inc_line_num, final_resolved))
            else:
                expanded.append((line, file_path, line_num, None))

        return expanded, includes

    def _parse_attributes(self, lines: list[str]) -> dict[str, str]:
        """Parse document attributes from lines.

        Attributes are defined as :name: value at the start of the document.

        Args:
            lines: Document lines

        Returns:
            Dictionary of attribute name to value
        """
        attributes: dict[str, str] = {}

        for line in lines:
            match = ATTRIBUTE_PATTERN.match(line)
            if match:
                name = match.group(1)
                value = match.group(2).strip()
                attributes[name] = value
            elif line.strip() and not line.startswith(":"):
                # Stop parsing attributes when we hit non-attribute content
                # (but continue through empty lines)
                if SECTION_PATTERN.match(line):
                    break

        return attributes

    def _substitute_attributes(self, text: str, attributes: dict[str, str]) -> str:
        """Substitute attribute references in text.

        Replaces {attribute} with the attribute value.

        Args:
            text: Text with potential attribute references
            attributes: Dictionary of attribute name to value

        Returns:
            Text with attribute references substituted
        """
        result = text
        for name, value in attributes.items():
            result = result.replace(f"{{{name}}}", value)
        return result

    def _parse_sections(
        self,
        lines: list[tuple[str, Path, int, SourceLocation | None]],
        file_path: Path,
        attributes: dict[str, str] | None = None,
    ) -> tuple[list[Section], str]:
        """Parse sections from document lines.

        Args:
            lines: Expanded lines with source info (line, file, line_num, resolved_from)
            file_path: Path to the main source file
            attributes: Document attributes for substitution

        Returns:
            Tuple of (list of top-level sections, document title)
        """
        if not lines:
            return [], ""

        if attributes is None:
            attributes = {}

        sections: list[Section] = []
        section_stack: list[Section] = []
        document_title = ""
        # Track used paths for disambiguation (Issue #123)
        used_paths: dict[str, int] = {}
        # Calculate file prefix for cross-document unique paths (Issue #130, ADR-008)
        file_prefix = self._get_file_prefix(file_path)

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

        for line_text, source_file, line_num, resolved_from in lines:
            match = SECTION_PATTERN.match(line_text)
            if match:
                equals = match.group(1)
                raw_title = match.group(2).strip()
                # Substitute attribute references in title
                title = self._substitute_attributes(raw_title, attributes)
                level = len(equals) - 1  # = is level 0, == is level 1, etc.

                # Create section with proper source location
                source_location = SourceLocation(
                    file=source_file,
                    line=line_num,
                    resolved_from=resolved_from,
                )

                section = Section(
                    title=title,
                    level=level,
                    path="",  # Will be set below
                    source_location=source_location,
                    children=[],
                    anchor=None,
                )

                # Document title (level 0)
                if level == 0:
                    document_title = title
                    # Issue #130, ADR-008: Document title path is the file prefix
                    section.path = file_prefix
                    sections.append(section)
                    section_stack = [section]
                else:
                    # Find parent section
                    while section_stack and section_stack[-1].level >= level:
                        section_stack.pop()

                    slug = _title_to_slug(title)
                    if section_stack:
                        parent = section_stack[-1]
                        # Issue #130, ADR-008: Build section path with file prefix
                        if parent.level == 0:
                            # Direct child of document title
                            section_path = slug
                        else:
                            # Extract section_path from parent (part after the colon)
                            if ":" in parent.path:
                                parent_section_path = parent.path.split(":", 1)[1]
                            else:
                                parent_section_path = parent.path
                            section_path = f"{parent_section_path}.{slug}"
                        # Full path is file_prefix:section_path
                        full_path = f"{file_prefix}:{section_path}"
                        # Get unique path (Issue #123: disambiguate duplicates)
                        section.path = get_unique_path(full_path)
                        parent.children.append(section)
                    else:
                        # No parent found, add as top-level with file prefix
                        full_path = f"{file_prefix}:{slug}"
                        # Get unique path (Issue #123: disambiguate duplicates)
                        section.path = get_unique_path(full_path)
                        sections.append(section)

                    section_stack.append(section)

        return sections, document_title

    def _compute_end_lines(
        self,
        sections: list[Section],
        lines: list[tuple[str, Path, int, SourceLocation | None]],
    ) -> None:
        """Compute end_line for all sections.

        For each section, end_line is set to the line before the next section
        starts in the same file, or the last line of the file.

        Args:
            sections: List of parsed sections (modified in place)
            lines: Expanded lines with source info
        """
        # Collect all sections with their file paths and start lines
        all_sections: list[Section] = []
        self._collect_all_sections(sections, all_sections)

        if not all_sections:
            return

        # Group sections by file
        sections_by_file: dict[Path, list[Section]] = {}
        for section in all_sections:
            file_path = section.source_location.file
            if file_path not in sections_by_file:
                sections_by_file[file_path] = []
            sections_by_file[file_path].append(section)

        # Count lines per file from expanded lines
        lines_per_file: dict[Path, int] = {}
        for _, source_file, line_num, _ in lines:
            if source_file not in lines_per_file:
                lines_per_file[source_file] = line_num
            else:
                lines_per_file[source_file] = max(lines_per_file[source_file], line_num)

        # For each file, sort sections by start line and compute end_line
        for file_path, file_sections in sections_by_file.items():
            # Sort by start line
            file_sections.sort(key=lambda s: s.source_location.line)

            # Get max line number for this file
            max_line = lines_per_file.get(file_path, 0)

            # Compute end_line for each section
            for i, section in enumerate(file_sections):
                if i + 1 < len(file_sections):
                    # Next section starts, our section ends one line before
                    next_start = file_sections[i + 1].source_location.line
                    section.source_location.end_line = next_start - 1
                else:
                    # Last section in file, ends at file end
                    section.source_location.end_line = max_line

    def _collect_all_sections(
        self, sections: list[Section], result: list[Section]
    ) -> None:
        """Recursively collect all sections into a flat list.

        Args:
            sections: List of sections to process
            result: List to append sections to (modified in place)
        """
        for section in sections:
            result.append(section)
            self._collect_all_sections(section.children, result)

    def _parse_elements(
        self,
        lines: list[tuple[str, Path, int, SourceLocation | None]],
        sections: list[Section],
        attributes: dict[str, str],
    ) -> list[Element]:
        """Parse elements from document lines.

        Args:
            lines: Expanded lines with source info
            sections: Parsed sections for parent context
            attributes: Document attributes for substitution

        Returns:
            List of extracted elements
        """
        elements: list[Element] = []
        current_section_path = ""
        pending_code_language: str | None = None
        pending_plantuml_info: tuple[str | None, str | None] | None = None
        pending_mermaid_info: tuple[str | None, str | None] | None = None
        pending_ditaa_info: tuple[str | None, str | None] | None = None
        in_code_block = False
        in_plantuml_block = False
        in_mermaid_block = False
        in_ditaa_block = False
        in_table = False
        current_list_type: str | None = None  # Track if we're in a list
        current_block_element: Element | None = None  # Track current block for end_line

        for line_text, source_file, line_num, resolved_from in lines:
            # Track current section for parent_section
            section_match = SECTION_PATTERN.match(line_text)
            if section_match:
                title = section_match.group(2).strip()
                # Apply attribute substitution to section titles so they match
                # the substituted titles stored in `sections`.
                if attributes:
                    def _sub_attr(match: re.Match) -> str:
                        name = match.group(1)
                        return attributes.get(name, match.group(0))

                    title = re.sub(r"\{([^}]+)\}", _sub_attr, title)
                current_section_path = self._find_section_path(sections, title)
                continue

            # Detect code block attribute [source,language]
            code_attr_match = CODE_BLOCK_START_PATTERN.match(line_text)
            if code_attr_match:
                pending_code_language = code_attr_match.group(1)
                continue

            # Detect plantuml block attribute [plantuml,name,format]
            plantuml_attr_match = PLANTUML_BLOCK_START_PATTERN.match(line_text)
            if plantuml_attr_match:
                name = plantuml_attr_match.group(1)
                fmt = plantuml_attr_match.group(2)
                pending_plantuml_info = (name, fmt)
                continue

            # Detect mermaid block attribute [mermaid,name,format]
            mermaid_attr_match = MERMAID_BLOCK_START_PATTERN.match(line_text)
            if mermaid_attr_match:
                name = mermaid_attr_match.group(1)
                fmt = mermaid_attr_match.group(2)
                pending_mermaid_info = (name, fmt)
                continue

            # Detect ditaa block attribute [ditaa,name,format]
            ditaa_attr_match = DITAA_BLOCK_START_PATTERN.match(line_text)
            if ditaa_attr_match:
                name = ditaa_attr_match.group(1)
                fmt = ditaa_attr_match.group(2)
                pending_ditaa_info = (name, fmt)
                continue

            # Detect listing delimiter ----
            if LISTING_DELIMITER_PATTERN.match(line_text):
                in_any_block = (
                    in_code_block or in_plantuml_block or in_mermaid_block or in_ditaa_block
                )
                if not in_any_block:
                    if pending_plantuml_info is not None:
                        # Start of plantuml block
                        in_plantuml_block = True
                        name, fmt = pending_plantuml_info
                        source_location = SourceLocation(
                            file=source_file,
                            line=line_num,
                            resolved_from=resolved_from,
                        )
                        # Only add attributes if they are not None
                        attrs: dict[str, str] = {}
                        if name is not None:
                            attrs["name"] = name
                        if fmt is not None:
                            attrs["format"] = fmt
                        element = Element(
                            type="plantuml",
                            source_location=source_location,
                            attributes=attrs,
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_block_element = element
                        pending_plantuml_info = None
                    elif pending_mermaid_info is not None:
                        # Start of mermaid block
                        in_mermaid_block = True
                        name, fmt = pending_mermaid_info
                        source_location = SourceLocation(
                            file=source_file,
                            line=line_num,
                            resolved_from=resolved_from,
                        )
                        attrs = {}
                        if name is not None:
                            attrs["name"] = name
                        if fmt is not None:
                            attrs["format"] = fmt
                        element = Element(
                            type="mermaid",
                            source_location=source_location,
                            attributes=attrs,
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_block_element = element
                        pending_mermaid_info = None
                    elif pending_ditaa_info is not None:
                        # Start of ditaa block
                        in_ditaa_block = True
                        name, fmt = pending_ditaa_info
                        source_location = SourceLocation(
                            file=source_file,
                            line=line_num,
                            resolved_from=resolved_from,
                        )
                        attrs = {}
                        if name is not None:
                            attrs["name"] = name
                        if fmt is not None:
                            attrs["format"] = fmt
                        element = Element(
                            type="ditaa",
                            source_location=source_location,
                            attributes=attrs,
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_block_element = element
                        pending_ditaa_info = None
                    elif pending_code_language is not None:
                        # Start of code block
                        in_code_block = True
                        source_location = SourceLocation(
                            file=source_file,
                            line=line_num,
                            resolved_from=resolved_from,
                        )
                        element = Element(
                            type="code",
                            source_location=source_location,
                            attributes={"language": pending_code_language},
                            parent_section=current_section_path,
                        )
                        elements.append(element)
                        current_block_element = element
                    pending_code_language = None
                elif in_code_block:
                    # End of code block
                    in_code_block = False
                    if current_block_element is not None:
                        current_block_element.source_location.end_line = line_num
                        current_block_element = None
                elif in_plantuml_block:
                    # End of plantuml block
                    in_plantuml_block = False
                    if current_block_element is not None:
                        current_block_element.source_location.end_line = line_num
                        current_block_element = None
                elif in_mermaid_block:
                    # End of mermaid block
                    in_mermaid_block = False
                    if current_block_element is not None:
                        current_block_element.source_location.end_line = line_num
                        current_block_element = None
                elif in_ditaa_block:
                    # End of ditaa block
                    in_ditaa_block = False
                    if current_block_element is not None:
                        current_block_element.source_location.end_line = line_num
                        current_block_element = None
                continue

            # Detect table delimiter |===
            if TABLE_DELIMITER_PATTERN.match(line_text):
                if not in_table:
                    # Start of table
                    in_table = True
                    source_location = SourceLocation(
                        file=source_file,
                        line=line_num,
                        resolved_from=resolved_from,
                    )
                    element = Element(
                        type="table",
                        source_location=source_location,
                        attributes={},
                        parent_section=current_section_path,
                    )
                    elements.append(element)
                    current_block_element = element
                else:
                    # End of table
                    in_table = False
                    if current_block_element is not None:
                        current_block_element.source_location.end_line = line_num
                        current_block_element = None
                continue

            # Detect image macro
            image_match = IMAGE_PATTERN.match(line_text)
            if image_match:
                target = image_match.group(1)
                alt_text = image_match.group(2) or ""
                source_location = SourceLocation(
                    file=source_file,
                    line=line_num,
                    end_line=line_num,  # Single-line element
                    resolved_from=resolved_from,
                )
                elements.append(
                    Element(
                        type="image",
                        source_location=source_location,
                        attributes={"target": target, "alt": alt_text},
                        parent_section=current_section_path,
                    )
                )
                continue

            # Detect admonition
            admonition_match = ADMONITION_PATTERN.match(line_text)
            if admonition_match:
                admonition_type = admonition_match.group(1)
                content = admonition_match.group(2)
                source_location = SourceLocation(
                    file=source_file,
                    line=line_num,
                    end_line=line_num,  # Single-line element
                    resolved_from=resolved_from,
                )
                elements.append(
                    Element(
                        type="admonition",
                        source_location=source_location,
                        attributes={"admonition_type": admonition_type, "content": content},
                        parent_section=current_section_path,
                    )
                )
                current_list_type = None  # Reset list tracking
                continue

            # Detect lists (unordered, ordered, description)
            # Check for unordered list (* item)
            if UNORDERED_LIST_PATTERN.match(line_text):
                if current_list_type != "unordered":
                    # Start of a new unordered list
                    current_list_type = "unordered"
                    source_location = SourceLocation(
                        file=source_file,
                        line=line_num,
                        resolved_from=resolved_from,
                    )
                    elements.append(
                        Element(
                            type="list",
                            source_location=source_location,
                            attributes={"list_type": "unordered"},
                            parent_section=current_section_path,
                        )
                    )
                continue

            # Check for ordered list (. item)
            if ORDERED_LIST_PATTERN.match(line_text):
                if current_list_type != "ordered":
                    # Start of a new ordered list
                    current_list_type = "ordered"
                    source_location = SourceLocation(
                        file=source_file,
                        line=line_num,
                        resolved_from=resolved_from,
                    )
                    elements.append(
                        Element(
                            type="list",
                            source_location=source_location,
                            attributes={"list_type": "ordered"},
                            parent_section=current_section_path,
                        )
                    )
                continue

            # Check for description list (term:: definition)
            if DESCRIPTION_LIST_PATTERN.match(line_text):
                if current_list_type != "description":
                    # Start of a new description list
                    current_list_type = "description"
                    source_location = SourceLocation(
                        file=source_file,
                        line=line_num,
                        resolved_from=resolved_from,
                    )
                    elements.append(
                        Element(
                            type="list",
                            source_location=source_location,
                            attributes={"list_type": "description"},
                            parent_section=current_section_path,
                        )
                    )
                continue

            # If line is not a list item, reset list tracking
            if line_text.strip():
                current_list_type = None

        return elements

    def _find_section_path(self, sections: list[Section], title: str) -> str:
        """Find the path of a section by its title.

        Args:
            sections: List of sections to search
            title: Title to find

        Returns:
            Section path or empty string if not found
        """
        for section in sections:
            if section.title == title:
                return section.path
            # Search in children
            result = self._find_section_path(section.children, title)
            if result:
                return result
        return ""

    def _parse_cross_references(
        self,
        lines: list[tuple[str, Path, int, SourceLocation | None]],
    ) -> list[CrossReference]:
        """Parse cross-references from document lines.

        Args:
            lines: Expanded lines with source info

        Returns:
            List of extracted cross-references
        """
        cross_references: list[CrossReference] = []

        for line_text, source_file, line_num, resolved_from in lines:
            # Find all cross-references in the line
            for match in XREF_PATTERN.finditer(line_text):
                target = match.group(1).strip()
                display_text = match.group(2)
                if display_text:
                    display_text = display_text.strip()

                source_location = SourceLocation(
                    file=source_file,
                    line=line_num,
                    resolved_from=resolved_from,
                )

                cross_references.append(
                    CrossReference(
                        type="internal",
                        target=target,
                        source_location=source_location,
                        text=display_text,
                    )
                )

        return cross_references
