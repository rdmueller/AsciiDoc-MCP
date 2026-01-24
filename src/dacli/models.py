"""Core data models for MCP Documentation Server.

This module defines the shared data models used across all parsers and services.
All models are implemented as dataclasses for simplicity and spec conformity.
JSON serialization is provided via the model_to_dict() helper function.

Models:
- SourceLocation: Position in source document with include tracking
- Section: Hierarchical document section
- Element: Extractable content element (code, table, image, etc.)
- CrossReference: Internal and external references
- Document: Base class for parsed documents
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class WarningType(Enum):
    """Types of warnings that can be detected during parsing."""

    UNCLOSED_BLOCK = "unclosed_block"
    UNCLOSED_TABLE = "unclosed_table"


@dataclass
class SourceLocation:
    """Position in a source document.

    Tracks the original file and line number, with optional tracking
    of include resolution for files that were included from another file.

    Attributes:
        file: Path to the source file
        line: 1-based line number (start line)
        end_line: 1-based end line number (inclusive), None if unknown
        resolved_from: If this content was included from another file,
                       the path to that file (None if not included)
    """

    file: Path
    line: int
    end_line: int | None = None
    resolved_from: Path | None = None


@dataclass
class Section:
    """A hierarchical section in a document.

    Represents a heading/section in the document with its position,
    hierarchical path, and optional children.

    Attributes:
        title: The section title/heading text
        level: Nesting level (0=document title, 1=chapter, 2=section, etc.)
        path: Hierarchical path (e.g., "chapter-1.section-2")
        source_location: Position in the source file
        children: Child sections (sub-sections)
        anchor: Optional explicit anchor ID (e.g., [[anchor]])
    """

    title: str
    level: int
    path: str
    source_location: SourceLocation
    children: list["Section"] = field(default_factory=list)
    anchor: str | None = None


@dataclass
class Element:
    """An extractable content element.

    Represents special content blocks like code, tables, images,
    PlantUML diagrams, or admonitions.

    Attributes:
        type: Element type (code, table, image, plantuml, admonition, list)
        source_location: Position in the source file
        attributes: Type-specific attributes (e.g., language for code)
        parent_section: Path of the containing section
        index: 0-based index within the parent section (set during indexing)
    """

    type: Literal["code", "table", "image", "plantuml", "admonition", "list"]
    source_location: SourceLocation
    attributes: dict[str, Any]
    parent_section: str
    index: int = 0


@dataclass
class CrossReference:
    """A cross-reference in a document.

    Tracks internal (<<anchor>>) and external (xref:file#anchor[])
    references for link validation.

    Attributes:
        type: Reference type (internal or external)
        target: Target anchor or file#anchor
        text: Optional custom link text
        source_location: Position in the source file
    """

    type: Literal["internal", "external"]
    target: str
    source_location: SourceLocation
    text: str | None = None


@dataclass
class ParseWarning:
    """A warning detected during document parsing.

    Represents structural issues like unclosed blocks or malformed tables.

    Attributes:
        type: Warning type (from WarningType enum)
        file: Path to the file containing the issue
        line: Line number where the issue starts
        message: Human-readable description of the issue
    """

    type: WarningType
    file: Path
    line: int
    message: str


@dataclass
class Document:
    """Base class for parsed documents.

    Provides common fields shared by AsciidocDocument and MarkdownDocument.

    Attributes:
        file_path: Path to the document file
        title: Document title
        sections: List of top-level sections
        elements: List of extractable elements
        parse_warnings: Structural issues detected during parsing
    """

    file_path: Path
    title: str
    sections: list[Section] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    parse_warnings: list[ParseWarning] = field(default_factory=list)


def model_to_dict(obj: Any) -> Any:
    """Convert a dataclass model to a JSON-serializable dictionary.

    Handles Path objects by converting them to strings.
    Recursively processes nested dataclasses and lists.

    Args:
        obj: A dataclass instance or any value

    Returns:
        A JSON-serializable dictionary or value
    """
    if hasattr(obj, "__dataclass_fields__"):
        # It's a dataclass - convert to dict and process values
        result = {}
        for key, value in asdict(obj).items():
            result[key] = _convert_value(value)
        return result
    return obj


def _convert_value(value: Any) -> Any:
    """Convert a value to JSON-serializable format.

    Args:
        value: Any value to convert

    Returns:
        JSON-serializable version of the value
    """
    if isinstance(value, Path):
        return str(value)
    elif isinstance(value, Enum):
        return value.value
    elif isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_convert_value(item) for item in value]
    else:
        return value
