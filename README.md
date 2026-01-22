# dacli - Documentation Access CLI

[![CI](https://github.com/docToolchain/dacli/actions/workflows/ci.yml/badge.svg)](https://github.com/docToolchain/dacli/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Navigate and query large documentation projects. Supports AsciiDoc and Markdown with hierarchical, content-aware access. Available as CLI tool and [MCP](https://modelcontextprotocol.io/) server for LLM integration.

Part of the [docToolchain](https://doctoolchain.org/) ecosystem.

## Features

- **Hierarchical Navigation** - Browse documentation structure with configurable depth
- **Content Access** - Read sections, extract code blocks, tables, and other elements
- **Full-Text Search** - Search across all indexed documentation content
- **Document Manipulation** - Update sections and insert new content with optimistic locking
- **Structure Validation** - Detect orphaned files and structural issues
- **Multi-Format Support** - Works with both AsciiDoc and Markdown files

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/docToolchain/dacli.git
cd dacli

# Install dependencies
uv sync
```

### CLI Usage

```bash
# Show help
uv run dacli --help

# Get document structure
uv run dacli --docs-root /path/to/docs structure --max-depth 2

# Read a section
uv run dacli section introduction.goals

# Search documentation
uv run dacli search "authentication" --max-results 10

# Validate structure
uv run dacli validate
```

All commands output text by default for human readability. Use `--format json` or `--format yaml` for machine-parseable output, and `--pretty` for formatted JSON output.

For full CLI documentation, see [06_cli_specification.adoc](src/docs/spec/06_cli_specification.adoc).

### MCP Server (for LLM integration)

```bash
uv run dacli-mcp --docs-root /path/to/your/docs
```

#### Claude Desktop Configuration

Add to your Claude Desktop config (`~/.config/claude-desktop/config.json` on Linux, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "dacli": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/dacli",
        "dacli-mcp",
        "--docs-root", "/path/to/your/documentation"
      ]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_structure` | Get hierarchical document structure with configurable depth |
| `get_section` | Read content of a specific section by path |
| `get_sections_at_level` | Get all sections at a specific nesting level |
| `search` | Full-text search across documentation |
| `get_elements` | Get code blocks, tables, images, and other elements |
| `get_metadata` | Get project or section metadata (word count, timestamps) |
| `validate_structure` | Validate documentation structure |
| `update_section` | Update section content with optimistic locking |
| `insert_content` | Insert new content before/after sections |

For detailed tool documentation, see the [User Manual](src/docs/50-user-manual/).

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linter
uv run ruff check src tests

# Format code
uv run ruff format src tests
```

## Architecture

The tool uses an in-memory index built from parsed documentation files at startup. Key components:

- **Document Parsers** - Parse AsciiDoc (with include resolution) and Markdown
- **Structure Index** - In-memory hierarchical index for fast lookups
- **MCP Tools** - FastMCP-based tools for LLM interaction
- **File Handler** - Atomic file operations with backup strategy

For detailed architecture documentation, see [src/docs/arc42/](src/docs/arc42/).

## License

MIT
