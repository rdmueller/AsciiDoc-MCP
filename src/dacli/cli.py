"""dacli - Docs-As-Code CLI.

Command-line interface for documentation navigation and manipulation.
Enables LLMs without MCP support to access documentation via bash/shell.

Usage:
    dacli [OPTIONS] <COMMAND> [ARGS]

Commands:
    structure          Get hierarchical document structure
    section            Read content of a specific section
    sections-at-level  Get all sections at a specific level
    search             Search documentation content
    elements           Get elements (code, tables, images)
    metadata           Get project or section metadata
    validate           Validate document structure
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
from dacli.file_utils import find_doc_files
from dacli.markdown_parser import MarkdownStructureParser
from dacli.mcp_app import _build_index, _get_section_end_line
from dacli.structure_index import StructureIndex

# Exit codes as specified in 06_cli_specification.adoc
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_PATH_NOT_FOUND = 3
EXIT_VALIDATION_ERROR = 4
EXIT_WRITE_ERROR = 5


class CliContext:
    """Shared context for CLI commands."""

    def __init__(
        self,
        docs_root: Path,
        output_format: str,
        pretty: bool,
        quiet: bool = False,
        respect_gitignore: bool = True,
        include_hidden: bool = False,
    ):
        self.docs_root = docs_root
        self.output_format = output_format
        self.pretty = pretty
        self.quiet = quiet
        self.respect_gitignore = respect_gitignore
        self.include_hidden = include_hidden

        # Configure logging level based on quiet flag
        if quiet:
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


@click.group()
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
    "--quiet", "-q",
    is_flag=True,
    default=False,
    help="Suppress warning messages (errors are still shown)",
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
    quiet: bool,
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
        quiet,
        respect_gitignore=not no_gitignore,
        include_hidden=include_hidden,
    )


@cli.command()
@click.option("--max-depth", type=int, default=None, help="Maximum depth to return")
@pass_context
def structure(ctx: CliContext, max_depth: int | None):
    """Get the hierarchical document structure."""
    result = ctx.index.get_structure(max_depth)
    click.echo(format_output(ctx, result))


@cli.command()
@click.argument("path")
@pass_context
def section(ctx: CliContext, path: str):
    """Read the content of a specific section."""
    normalized_path = path.lstrip("/")

    section_obj = ctx.index.get_section(normalized_path)
    if section_obj is None:
        suggestions = ctx.index.get_suggestions(normalized_path)
        result = {
            "error": {
                "code": "PATH_NOT_FOUND",
                "message": f"Section '{normalized_path}' not found",
                "details": {
                    "requested_path": normalized_path,
                    "suggestions": suggestions,
                },
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


@cli.command("sections-at-level")
@click.argument("level", type=int)
@pass_context
def sections_at_level(ctx: CliContext, level: int):
    """Get all sections at a specific nesting level."""
    sections = ctx.index.get_sections_at_level(level)
    result = {
        "level": level,
        "sections": [{"path": s.path, "title": s.title} for s in sections],
        "count": len(sections),
    }
    click.echo(format_output(ctx, result))


@cli.command()
@click.argument("query")
@click.option("--scope", default=None, help="Path prefix to limit search scope")
@click.option("--max-results", type=int, default=50, help="Maximum results to return")
@pass_context
def search(ctx: CliContext, query: str, scope: str | None, max_results: int):
    """Search for content in the documentation."""
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


@cli.command()
@click.option("--type", "element_type", default=None,
              help="Element type: code, table, image, diagram, list")
@click.option("--section", "section_path", default=None,
              help="Filter by section path")
@pass_context
def elements(ctx: CliContext, element_type: str | None, section_path: str | None):
    """Get elements (code blocks, tables, images) from documentation."""
    elems = ctx.index.get_elements(
        element_type=element_type,
        section_path=section_path,
    )

    def build_preview(elem) -> str | None:
        attrs = elem.attributes
        if elem.type == "plantuml":
            parts = ["plantuml"]
            if attrs.get("name"):
                parts.append(attrs["name"])
            if attrs.get("format"):
                parts.append(attrs["format"])
            return f"[{', '.join(parts)}]"
        elif elem.type == "code":
            lang = attrs.get("language", "")
            return f"[source, {lang}]" if lang else "[source]"
        elif elem.type == "image":
            target = attrs.get("target", "")
            alt = attrs.get("alt", "")
            return f"image::{target}[{alt}]"
        elif elem.type == "table":
            return "|==="
        elif elem.type == "admonition":
            atype = attrs.get("admonition_type", "NOTE")
            full_content = attrs.get("content", "")
            if len(full_content) > 30:
                return f"{atype}: {full_content[:30]}..."
            return f"{atype}: {full_content}"
        elif elem.type == "list":
            list_type = attrs.get("list_type", "unordered")
            return f"{list_type} list"
        return None

    result = {
        "elements": [
            {
                "type": e.type,
                "parent_section": e.parent_section,
                "location": {
                    "file": str(e.source_location.file),
                    "start_line": e.source_location.line,
                    "end_line": e.source_location.end_line,
                },
                "preview": build_preview(e),
            }
            for e in elems
        ],
        "count": len(elems),
    }
    click.echo(format_output(ctx, result))


@cli.command()
@click.argument("path", required=False, default=None)
@pass_context
def metadata(ctx: CliContext, path: str | None):
    """Get metadata about the project or a specific section."""
    from datetime import UTC, datetime

    if path is None:
        # Project-level metadata
        stats = ctx.index.stats()
        files = set(ctx.index._file_to_sections.keys())

        total_words = 0
        for content in ctx.index._section_content.values():
            total_words += len(content.split())

        last_modified = None
        for file_path in files:
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                if last_modified is None or mtime > last_modified:
                    last_modified = mtime

        formats = set()
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext == ".adoc":
                formats.add("asciidoc")
            elif ext == ".md":
                formats.add("markdown")

        result = {
            "path": None,
            "total_files": len(files),
            "total_sections": stats["total_sections"],
            "total_words": total_words,
            "last_modified": (
                datetime.fromtimestamp(last_modified, tz=UTC).isoformat()
                if last_modified
                else None
            ),
            "formats": sorted(formats),
        }
        click.echo(format_output(ctx, result))
    else:
        normalized_path = path.lstrip("/")
        section_obj = ctx.index.get_section(normalized_path)

        if section_obj is None:
            result = {"error": f"Section '{normalized_path}' not found"}
            click.echo(format_output(ctx, result))
            sys.exit(EXIT_PATH_NOT_FOUND)

        content = ctx.index._section_content.get(normalized_path, "")
        word_count = len(content.split())

        file_path = section_obj.source_location.file
        last_modified = None
        if file_path.exists():
            from datetime import UTC, datetime
            mtime = file_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

        subsection_count = len(section_obj.children)

        result = {
            "path": normalized_path,
            "title": section_obj.title,
            "file": str(file_path),
            "word_count": word_count,
            "last_modified": last_modified,
            "subsection_count": subsection_count,
        }
        click.echo(format_output(ctx, result))


@cli.command()
@pass_context
def validate(ctx: CliContext):
    """Validate the document structure."""
    import time

    start_time = time.time()
    errors: list[dict] = []
    warnings: list[dict] = []

    indexed_files = set(ctx.index._file_to_sections.keys())

    all_doc_files: set[Path] = set()
    for adoc_file in find_doc_files(ctx.docs_root, "*.adoc"):
        all_doc_files.add(adoc_file.resolve())
    for md_file in find_doc_files(ctx.docs_root, "*.md"):
        if md_file.name not in ("CLAUDE.md", "README.md"):
            all_doc_files.add(md_file.resolve())

    indexed_resolved = {f.resolve() for f in indexed_files}
    for doc_file in all_doc_files:
        if doc_file not in indexed_resolved:
            rel_path = doc_file.relative_to(ctx.docs_root.resolve())
            warnings.append({
                "type": "orphaned_file",
                "path": str(rel_path),
                "message": "File is not included in any document",
            })

    elapsed_ms = int((time.time() - start_time) * 1000)

    is_valid = len(errors) == 0
    result = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "validation_time_ms": elapsed_ms,
    }
    click.echo(format_output(ctx, result))

    if not is_valid:
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
    import hashlib

    normalized_path = path.lstrip("/")
    preserve_title = not no_preserve_title

    section_obj = ctx.index.get_section(normalized_path)
    if section_obj is None:
        result = {"success": False, "error": f"Section '{normalized_path}' not found"}
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_PATH_NOT_FOUND)

    file_path = section_obj.source_location.file
    start_line = section_obj.source_location.line
    end_line = _get_section_end_line(section_obj, file_path, ctx.file_handler)

    try:
        file_content = ctx.file_handler.read_file(file_path)
        lines = file_content.splitlines(keepends=True)
        current_content = "".join(lines[start_line - 1 : end_line])
        previous_hash = hashlib.md5(current_content.encode("utf-8")).hexdigest()[:8]
    except FileReadError:
        previous_hash = ""

    if expected_hash is not None and expected_hash != previous_hash:
        result = {
            "success": False,
            "error": f"Hash conflict: expected '{expected_hash}', got '{previous_hash}'",
            "current_hash": previous_hash,
        }
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_ERROR)

    new_content = content
    if preserve_title:
        stripped_content = new_content.lstrip()
        has_explicit_title = stripped_content.startswith("=") or stripped_content.startswith("#")
        if not has_explicit_title:
            file_ext = file_path.suffix.lower()
            if file_ext in (".adoc", ".asciidoc"):
                level_markers = "=" * (section_obj.level + 1)
            else:
                level_markers = "#" * (section_obj.level + 1)
            new_content = f"{level_markers} {section_obj.title}\n\n{new_content}"

    if not new_content.endswith("\n"):
        new_content += "\n"

    new_hash = hashlib.md5(new_content.encode("utf-8")).hexdigest()[:8]

    try:
        ctx.file_handler.update_section(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
            new_content=new_content,
        )
        result = {
            "success": True,
            "path": normalized_path,
            "location": {"file": str(file_path), "line": start_line},
            "previous_hash": previous_hash,
            "new_hash": new_hash,
        }
        click.echo(format_output(ctx, result))
    except FileWriteError as e:
        result = {"success": False, "error": f"Failed to write: {e}"}
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_WRITE_ERROR)


@cli.command()
@click.argument("path")
@click.option("--position", required=True, type=click.Choice(["before", "after", "append"]),
              help="Where to insert: before, after, or append")
@click.option("--content", required=True, help="Content to insert")
@pass_context
def insert(ctx: CliContext, path: str, position: str, content: str):
    """Insert content relative to a section."""
    import hashlib

    normalized_path = path.lstrip("/")

    section_obj = ctx.index.get_section(normalized_path)
    if section_obj is None:
        result = {"success": False, "error": f"Section '{normalized_path}' not found"}
        click.echo(format_output(ctx, result))
        sys.exit(EXIT_PATH_NOT_FOUND)

    file_path = section_obj.source_location.file
    start_line = section_obj.source_location.line
    end_line = _get_section_end_line(section_obj, file_path, ctx.file_handler)

    insert_content = content
    if not insert_content.endswith("\n"):
        insert_content += "\n"

    try:
        file_content = ctx.file_handler.read_file(file_path)
        previous_hash = hashlib.md5(file_content.encode("utf-8")).hexdigest()[:8]
        lines = file_content.splitlines(keepends=True)

        if position == "before":
            insert_line = start_line
            new_lines = lines[: start_line - 1] + [insert_content] + lines[start_line - 1 :]
        elif position == "after":
            insert_line = end_line + 1
            new_lines = lines[:end_line] + [insert_content] + lines[end_line:]
        else:  # append
            insert_line = end_line
            new_lines = lines[: end_line - 1] + [insert_content] + lines[end_line - 1 :]

        new_file_content = "".join(new_lines)
        new_hash = hashlib.md5(new_file_content.encode("utf-8")).hexdigest()[:8]

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
