"""dacli - Docs-As-Code CLI.

Command-line interface for documentation navigation and manipulation.
Enables LLMs without MCP support to access documentation via bash/shell.

Usage:
    dacli [OPTIONS] <COMMAND> [ARGS]

Commands (with aliases):
    structure (str)    Get hierarchical document structure
    metadata (meta)    Get project or section metadata
    search (s)         Search documentation content
    sections-at-level (lv)  Get all sections at a specific level
    section (sec)      Read content of a specific section
    elements (el)      Get elements (code, tables, images)
    validate (val)     Validate document structure
    update             Update section content
    insert             Insert content relative to a section
"""

import json
import logging
import sys
from pathlib import Path

import click

from dacli import __version__
from dacli.asciidoc_parser import AsciidocStructureParser
from dacli.file_handler import FileReadError, FileSystemHandler, FileWriteError
from dacli.markdown_parser import MarkdownStructureParser
from dacli.mcp_app import _build_index
from dacli.services import (
    compute_hash,
    get_project_metadata,
    get_section_metadata,
)
from dacli.services import (
    update_section as service_update_section,
)
from dacli.services import (
    validate_structure as service_validate_structure,
)
from dacli.services.content_service import _get_section_end_line
from dacli.structure_index import Section, StructureIndex


def _process_escape_sequences(content: str) -> str:
    """Process common escape sequences without corrupting non-ASCII characters.

    Handles \\n, \\t, \\r, and \\\\ escape sequences. Unlike decode('unicode_escape'),
    this preserves non-ASCII characters like umlauts (äöü) correctly.

    Args:
        content: Input string potentially containing escape sequences

    Returns:
        String with escape sequences processed

    Issue #193: Fixed encoding problem with umlauts
    """
    # Process escape sequences in order (most specific first)
    # Must process \\\\ first to avoid double-processing
    return (
        content
        .replace('\\\\', '\x00')  # Temp marker for literal backslash
        .replace('\\n', '\n')
        .replace('\\t', '\t')
        .replace('\\r', '\r')
        .replace('\x00', '\\')  # Restore literal backslash
    )


def _get_section_append_line(
    section: Section,
    index: StructureIndex,
    file_handler: FileSystemHandler,
) -> int:
    """Get the line number where content should be appended (after all descendants).

    For 'append' position, we need to find the end of the last descendant section,
    not just the end of the section's own content.

    Args:
        section: The parent section to append to
        index: Structure index for finding related sections
        file_handler: File handler for reading files

    Returns:
        The line number where content should be inserted (1-based)
    """
    file_path = section.source_location.file
    all_sections = index.get_sections_by_file(file_path)

    # Find all descendants (sections whose path starts with parent path)
    # Issue #197: Handle both ":" separator (doc:section) and "." (section.subsection)
    parent_path = section.path
    descendants = []
    for s in all_sections:
        # Skip the parent itself
        if s.path == parent_path:
            continue
        # Check if this is a descendant
        # Level 1 children use ":" separator (e.g., "doc:child")
        # Nested children use "." separator (e.g., "doc:child.grandchild")
        if parent_path == "":
            # Root document - all sections are descendants
            if s.path != "":
                descendants.append(s)
        elif s.path.startswith(parent_path + ":") or s.path.startswith(parent_path + "."):
            descendants.append(s)

    if not descendants:
        # No children, use section's own end line
        return _get_section_end_line(section, file_path, file_handler)

    # Find the descendant with the highest end line
    max_end_line = _get_section_end_line(section, file_path, file_handler)
    for desc in descendants:
        desc_end = _get_section_end_line(desc, file_path, file_handler)
        if desc_end > max_end_line:
            max_end_line = desc_end

    return max_end_line

# Exit codes as specified in 06_cli_specification.adoc
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_PATH_NOT_FOUND = 3
EXIT_VALIDATION_ERROR = 4
EXIT_WRITE_ERROR = 5

# Command aliases for shorter typing
COMMAND_ALIASES = {
    "s": "search",
    "sec": "section",
    "str": "structure",
    "meta": "metadata",
    "el": "elements",
    "val": "validate",
    "lv": "sections-at-level",
}

# Command groups for organized help output (story-based ordering)
COMMAND_GROUPS = {
    "Discover": ["structure", "metadata"],
    "Find": ["search", "sections-at-level"],
    "Read": ["section", "elements"],
    "Validate": ["validate"],
    "Edit": ["update", "insert"],
}

# Reverse lookup: command -> alias
COMMAND_TO_ALIAS = {v: k for k, v in COMMAND_ALIASES.items()}


class AliasedGroup(click.Group):
    """A Click group that supports command aliases, typo suggestions, and grouped help."""

    def get_command(self, ctx, cmd_name):
        """Resolve command name, checking aliases first."""
        # Check if it's an alias
        if cmd_name in COMMAND_ALIASES:
            cmd_name = COMMAND_ALIASES[cmd_name]
        return super().get_command(ctx, cmd_name)

    def resolve_command(self, ctx, args):
        """Resolve command with typo suggestions for unknown commands."""
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as e:
            # Check if this is an unknown command error
            if args and "No such command" in str(e):
                cmd_name = args[0]
                suggestion = self._get_suggestion(cmd_name)
                if suggestion:
                    raise click.UsageError(
                        f"No such command '{cmd_name}'.\n\n"
                        f"Did you mean: {suggestion}"
                    ) from e
            raise

    def _get_suggestion(self, cmd_name: str) -> str | None:
        """Find similar command names using fuzzy matching."""
        import difflib

        # Get all valid command names and aliases
        all_names = list(self.commands.keys()) + list(COMMAND_ALIASES.keys())

        # Find close matches
        matches = difflib.get_close_matches(cmd_name, all_names, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def format_commands(self, ctx, formatter):
        """Write commands in story-based groups."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        # Build command lookup
        cmd_lookup = {name: cmd for name, cmd in commands}

        # Format commands by group
        for group_name, group_cmds in COMMAND_GROUPS.items():
            rows = []
            for cmd_name in group_cmds:
                if cmd_name in cmd_lookup:
                    cmd = cmd_lookup[cmd_name]
                    help_text = cmd.get_short_help_str(limit=formatter.width)
                    # Add alias info
                    alias = COMMAND_TO_ALIAS.get(cmd_name, "")
                    if alias:
                        display_name = f"{cmd_name} ({alias})"
                    else:
                        display_name = cmd_name
                    rows.append((display_name, help_text))

            if rows:
                with formatter.section(group_name):
                    formatter.write_dl(rows)


class CliContext:
    """Shared context for CLI commands."""

    def __init__(
        self,
        docs_root: Path,
        output_format: str,
        pretty: bool,
        verbose: bool = False,
        respect_gitignore: bool = True,
        include_hidden: bool = False,
    ):
        self.docs_root = docs_root
        self.output_format = output_format
        self.pretty = pretty
        self.verbose = verbose
        self.respect_gitignore = respect_gitignore
        self.include_hidden = include_hidden

        # Configure logging level based on verbose flag
        # Default is quiet (ERROR only), verbose enables WARNING
        if not verbose:
            logging.getLogger().setLevel(logging.ERROR)

        self.index = StructureIndex()
        self.file_handler = FileSystemHandler()
        self.asciidoc_parser = AsciidocStructureParser(base_path=docs_root)
        self.markdown_parser = MarkdownStructureParser()

        # Build index
        _build_index(
            docs_root,
            self.index,
            self.asciidoc_parser,
            self.markdown_parser,
            respect_gitignore=respect_gitignore,
            include_hidden=include_hidden,
        )


def format_output(ctx: CliContext, data: dict) -> str:
    """Format output data according to the specified format."""
    if ctx.output_format == "json":
        if ctx.pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)
    elif ctx.output_format == "yaml":
        try:
            import yaml
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            return json.dumps(data, indent=2, default=str)
    else:  # text
        return _format_as_text(data)


def _format_as_text(data: dict, indent: int = 0) -> str:
    """Format data as human-readable text."""
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_as_text(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_format_as_text(item, indent + 1))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


pass_context = click.make_pass_decorator(CliContext)


@click.group(
    cls=AliasedGroup,
    epilog="""
\b
Examples:
  dacli --format json structure      # Get document structure as JSON
  dacli search "authentication"      # Find sections about authentication
  dacli section api.endpoints        # Read a specific section
""",
)
@click.option(
    "--docs-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Documentation root directory (default: current directory)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml", "text"]),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--pretty",
    is_flag=True,
    default=False,
    help="Pretty-print output for human readability",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show warning messages (default: only errors are shown)",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    default=False,
    help="Include files that would normally be excluded by .gitignore patterns",
)
@click.option(
    "--include-hidden",
    is_flag=True,
    default=False,
    help="Include files in hidden directories (starting with '.')",
)
@click.version_option(version=__version__, prog_name="dacli")
@click.pass_context
def cli(
    ctx,
    docs_root: Path,
    output_format: str,
    pretty: bool,
    verbose: bool,
    no_gitignore: bool,
    include_hidden: bool,
):
    """dacli - Docs-As-Code CLI.

    Access documentation structure, content, and metadata from the command line.
    Designed for LLM integration via bash/shell commands.
    """
    ctx.obj = CliContext(
        docs_root,
        output_format,
        pretty,
        verbose,
        respect_gitignore=not no_gitignore,
        include_hidden=include_hidden,
    )


@cli.command(epilog="""
Examples:
  dacli structure                    # Full structure
  dacli structure --max-depth 1      # Only top-level sections
  dacli --format json str            # JSON output using alias
""")
@click.option("--max-depth", type=int, default=None, help="Maximum depth to return")
@pass_context
def structure(ctx: CliContext, max_depth: int | None):
    """Get the hierarchical document structure."""
    result = ctx.index.get_structure(max_depth)
    click.echo(format_output(ctx, result))


@cli.command(epilog="""
Examples:
  dacli section introduction           # Read 'introduction' section
  dacli section api.endpoints          # Read nested section
  dacli --format json sec api          # JSON output using alias
""")
@click.argument("path")
@pass_context
def section(ctx: CliContext, path: str):
    """Read the content of a specific section."""
    normalized_path = path.lstrip("/")

    # Check for path format issues (Issue #198)
    corrected_path, had_extra_colons = ctx.index.normalize_path(normalized_path)

    section_obj = ctx.index.get_section(normalized_path)
    if section_obj is None:
        suggestions = ctx.index.get_suggestions(normalized_path)

        error_details = {
            "requested_path": normalized_path,
            "suggestions": suggestions,
        }

        # Add hint if user used multiple colons (Issue #198)
        if had_extra_colons:
            error_details["corrected_path"] = corrected_path
            error_details["hint"] = (
                "Use colon (:) only once to separate document from section. "
                "Use dots (.) for nested sections. "
                f"Example: {corrected_path}"
            )

        result = {
            "error": {
                "code": "PATH_NOT_FOUND",
                "message": f"Section '{normalized_path}' not found",
                "details": error_details,
            }
        }
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_PATH_NOT_FOUND)

    try:
        file_content = ctx.file_handler.read_file(section_obj.source_location.file)
        lines = file_content.splitlines()

        start_line = section_obj.source_location.line - 1
        end_line = section_obj.source_location.end_line
        if end_line is None:
            end_line = len(lines)

        content = "\n".join(lines[start_line:end_line])

        file_ext = section_obj.source_location.file.suffix.lower()
        doc_format = "asciidoc" if file_ext in (".adoc", ".asciidoc") else "markdown"

        result = {
            "path": section_obj.path,
            "title": section_obj.title,
            "content": content,
            "location": {
                "file": str(section_obj.source_location.file),
                "start_line": section_obj.source_location.line,
                "end_line": end_line,
            },
            "format": doc_format,
        }
        click.echo(format_output(ctx, result))
    except FileReadError as e:
        click.echo(format_output(ctx, {"error": f"Failed to read section: {e}"}))
        sys.exit(EXIT_ERROR)


@cli.command(
    "sections-at-level",
    context_settings={"ignore_unknown_options": True, "allow_interspersed_args": False},
    epilog="""
Examples:
  dacli sections-at-level 1        # All top-level chapters
  dacli sections-at-level 2        # All second-level sections
  dacli --format json lv 1         # JSON output using alias
""")
@click.argument("level", type=int)
@pass_context
def sections_at_level(ctx: CliContext, level: int):
    """Get all sections at a specific nesting level.

    LEVEL must be a non-negative integer (0, 1, 2, ...).
    """
    # Validate level is non-negative (Issue #199)
    if level < 0:
        raise click.BadParameter(
            f"Level must be non-negative, got {level}. "
            "Document hierarchies start at level 0 (document root).",
            param_hint="level"
        )

    sections = ctx.index.get_sections_at_level(level)
    result = {
        "level": level,
        "sections": [{"path": s.path, "title": s.title} for s in sections],
        "count": len(sections),
    }
    click.echo(format_output(ctx, result))


@cli.command(epilog="""
Examples:
  dacli search "authentication"              # Search all docs
  dacli search "API" --scope api             # Search within 'api' section
  dacli search "error" --limit 5             # Limit results
  dacli --format json s "database"           # JSON output using alias
""")
@click.argument("query")
@click.option("--scope", default=None, help="Path prefix to limit search scope")
@click.option(
    "--max-results", "--limit", type=int, default=20,
    help="Maximum results to return (default: 20)"
)
@pass_context
def search(ctx: CliContext, query: str, scope: str | None, max_results: int):
    """Search for content in the documentation."""
    # Validate query is not empty
    if not query or not query.strip():
        click.echo("Error: Search query cannot be empty", err=True)
        sys.exit(EXIT_INVALID_ARGS)

    results = ctx.index.search(
        query=query,
        scope=scope,
        case_sensitive=False,
        max_results=max_results,
    )
    result = {
        "query": query,
        "results": [
            {
                "path": r.path,
                "line": r.line,
                "context": r.context,
                "score": r.score,
            }
            for r in results
        ],
        "total_results": len(results),
    }
    click.echo(format_output(ctx, result))


@cli.command(epilog="""
Examples:
  dacli elements                             # All elements (metadata only)
  dacli elements --type code                 # Only code blocks
  dacli elements --include-content           # Include element content
  dacli elements --include-content --content-limit 10  # First 10 lines only
  dacli elements api --recursive             # Elements in 'api' and subsections
  dacli --format json el --type image        # JSON output using alias
""")
@click.argument("section_path", required=False, default=None)
@click.option("--type", "element_type", default=None,
              help="Element type: code, table, image, diagram, list")
@click.option("--recursive", is_flag=True, default=False,
              help="Include elements from child sections")
@click.option("--include-content", is_flag=True, default=False,
              help="Include element content (Issue #159)")
@click.option("--content-limit", type=int, default=None,
              help="Limit content to first N lines (requires --include-content)")
@pass_context
def elements(ctx: CliContext, section_path: str | None, element_type: str | None,
             recursive: bool, include_content: bool, content_limit: int | None):
    """Get elements (code blocks, tables, images) from documentation."""
    elems = ctx.index.get_elements(
        element_type=element_type,
        section_path=section_path,
        recursive=recursive,
    )

    # Build element dicts with optional content (Issue #159)
    element_dicts = []
    for e in elems:
        elem_dict = {
            "type": e.type,
            "parent_section": e.parent_section,
            "location": {
                "file": str(e.source_location.file),
                "start_line": e.source_location.line,
                "end_line": e.source_location.end_line,
            },
        }

        # Include attributes if requested (Issue #159)
        if include_content:
            attributes = dict(e.attributes)  # Copy attributes

            # Apply content limit if specified
            if content_limit is not None and "content" in attributes:
                content = attributes["content"]
                lines = content.split("\n")
                if len(lines) > content_limit:
                    attributes["content"] = "\n".join(lines[:content_limit])

            elem_dict["attributes"] = attributes

        element_dicts.append(elem_dict)

    result = {
        "elements": element_dicts,
        "count": len(element_dicts),
    }
    click.echo(format_output(ctx, result))


@cli.command(epilog="""
Examples:
  dacli metadata                     # Project-level metadata
  dacli metadata introduction        # Section metadata
  dacli --format json meta           # JSON output using alias
""")
@click.argument("path", required=False, default=None)
@pass_context
def metadata(ctx: CliContext, path: str | None):
    """Get metadata about the project or a specific section."""
    if path is None:
        result = get_project_metadata(ctx.index)
    else:
        result = get_section_metadata(ctx.index, path)
        if "error" in result:
            click.echo(format_output(ctx, result))
            sys.exit(EXIT_PATH_NOT_FOUND)
    click.echo(format_output(ctx, result))


@cli.command(epilog="""
Examples:
  dacli validate                     # Check for issues
  dacli --format json val            # JSON output using alias
""")
@pass_context
def validate(ctx: CliContext):
    """Validate the document structure."""
    result = service_validate_structure(ctx.index, ctx.docs_root)
    click.echo(format_output(ctx, result))

    if not result["valid"]:
        sys.exit(EXIT_VALIDATION_ERROR)


@cli.command()
@click.argument("path")
@click.option("--content", required=True, help="New section content")
@click.option("--no-preserve-title", is_flag=True, help="Don't preserve original title")
@click.option("--expected-hash", default=None, help="Hash for optimistic locking")
@pass_context
def update(ctx: CliContext, path: str, content: str, no_preserve_title: bool,
           expected_hash: str | None):
    """Update the content of a section."""
    # CLI-specific: read from stdin if "-", otherwise process escape sequences
    if content == "-":
        processed_content = sys.stdin.read()
    else:
        processed_content = _process_escape_sequences(content)

    result = service_update_section(
        index=ctx.index,
        file_handler=ctx.file_handler,
        path=path,
        content=processed_content,
        preserve_title=not no_preserve_title,
        expected_hash=expected_hash,
    )
    click.echo(format_output(ctx, result))

    if not result.get("success", False):
        if "not found" in result.get("error", ""):
            sys.exit(EXIT_PATH_NOT_FOUND)
        elif "Hash conflict" in result.get("error", ""):
            sys.exit(EXIT_ERROR)
        else:
            sys.exit(EXIT_WRITE_ERROR)


@cli.command()
@click.argument("path")
@click.option("--position", required=True, type=click.Choice(["before", "after", "append"]),
              help="Where to insert: before, after, or append")
@click.option("--content", required=True, help="Content to insert")
@pass_context
def insert(ctx: CliContext, path: str, position: str, content: str):
    """Insert content relative to a section."""
    normalized_path = path.lstrip("/")

    section_obj = ctx.index.get_section(normalized_path)
    if section_obj is None:
        result = {"success": False, "error": f"Section '{normalized_path}' not found"}
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_PATH_NOT_FOUND)

    file_path = section_obj.source_location.file
    start_line = section_obj.source_location.line
    end_line = _get_section_end_line(section_obj, file_path, ctx.file_handler)

    # Process content: read from stdin if "-", otherwise process escape sequences
    if content == "-":
        insert_content = sys.stdin.read()
    else:
        insert_content = _process_escape_sequences(content)
    if not insert_content.endswith("\n"):
        insert_content += "\n"

    try:
        file_content = ctx.file_handler.read_file(file_path)
        previous_hash = compute_hash(file_content)
        lines = file_content.splitlines(keepends=True)

        # Ensure blank line before headings when inserting after content
        stripped_insert = insert_content.lstrip()
        starts_with_heading = stripped_insert.startswith("#") or stripped_insert.startswith("=")

        def next_line_is_heading(lines: list, next_idx: int) -> bool:
            """Check if the line at next_idx starts with a heading marker."""
            if next_idx < len(lines):
                next_line = lines[next_idx].lstrip()
                return next_line.startswith("#") or next_line.startswith("=")
            return False

        def ensure_trailing_blank_line(content: str) -> str:
            """Ensure content ends with a blank line (two newlines)."""
            if not content.endswith("\n\n"):
                if content.endswith("\n"):
                    return content + "\n"
                return content + "\n\n"
            return content

        if position == "before":
            insert_line = start_line
            # Check if the line we're inserting before is a heading
            next_line_idx = start_line - 1  # 0-based index
            if next_line_is_heading(lines, next_line_idx) and not starts_with_heading:
                insert_content = ensure_trailing_blank_line(insert_content)
            new_lines = lines[: start_line - 1] + [insert_content] + lines[start_line - 1 :]
        elif position == "after":
            insert_line = end_line + 1
            # Add blank line before headings if previous line is not blank
            if starts_with_heading and end_line > 0:
                prev_line = lines[end_line - 1] if end_line <= len(lines) else ""
                if prev_line.strip():
                    insert_content = "\n" + insert_content
            # Add blank line after content if next line is a heading
            # 0-based index (end_line is 1-based, so lines[end_line] is the next line)
            next_line_idx = end_line
            if next_line_is_heading(lines, next_line_idx) and not starts_with_heading:
                insert_content = ensure_trailing_blank_line(insert_content)
            new_lines = lines[:end_line] + [insert_content] + lines[end_line:]
        else:  # append - insert after all descendants
            append_line = _get_section_append_line(section_obj, ctx.index, ctx.file_handler)
            insert_line = append_line + 1
            # Add blank line before headings if previous line is not blank
            if starts_with_heading and append_line > 0:
                prev_line = lines[append_line - 1] if append_line <= len(lines) else ""
                if prev_line.strip():
                    insert_content = "\n" + insert_content
            # Add blank line after content if next line is a heading
            next_line_idx = append_line  # 0-based index
            if next_line_is_heading(lines, next_line_idx) and not starts_with_heading:
                insert_content = ensure_trailing_blank_line(insert_content)
            new_lines = lines[:append_line] + [insert_content] + lines[append_line:]

        new_file_content = "".join(new_lines)
        new_hash = compute_hash(new_file_content)

        ctx.file_handler.write_file(file_path, new_file_content)

        result = {
            "success": True,
            "inserted_at": {"file": str(file_path), "line": insert_line},
            "previous_hash": previous_hash,
            "new_hash": new_hash,
        }
        click.echo(format_output(ctx, result))
    except (FileReadError, FileWriteError) as e:
        result = {"success": False, "error": f"Failed to insert: {e}"}
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_WRITE_ERROR)


if __name__ == "__main__":
    cli()
