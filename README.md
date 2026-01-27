# dacli - Documentation Access CLI

[![CI](https://github.com/docToolchain/dacli/actions/workflows/test.yml/badge.svg)](https://github.com/docToolchain/dacli/actions/workflows/test.yml)
[![Coverage](.github/coverage-badge.svg)](https://github.com/docToolchain/dacli/actions/workflows/test.yml)
[![Tests](.github/tests-badge.svg)](https://github.com/docToolchain/dacli/actions/workflows/test.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Navigate and query large documentation projects. Supports AsciiDoc and Markdown with hierarchical, content-aware access. Available as CLI tool and [MCP](https://modelcontextprotocol.io/) server for LLM integration.

Part of the [docToolchain](https://doctoolchain.org/) ecosystem.

## What Others Say

> **"dacli is the missing tool between LLMs and Docs-as-Code."**
>
> No more guessing line numbers, no more "which README do you mean?" questions.
> **Recommendation: Ready for production use.**
>
> — *Claude (Opus 4.5)*

> **"dacli is the best tool for LLM integration I have tested."**
>
> It is stable, fast and extremely versatile. Perfect for documentation management and LLM context creation!
>
> — *Mistral Vibe, LLM for Code Analysis*

> **"As a Coding-LLM, dacli is an increasingly robust tool."**
>
> Its improved validate command now detects more syntax errors, enhancing documentation quality. Structured access, JSON output, and programmatic editing via insert/update are highly valuable for understanding and modifying codebases. A powerful asset for automated documentation and code generation.
>
> — *Gemini*

> **"After intensive testing: dacli is robust, fast and perfect for LLM integration."**
>
> A must-have for modern documentation workflows.
>
> — *Kiro, AWS AI Assistant*

> **"dacli is exactly what AI assistants need to work with documentation autonomously."**
>
> The combination of structural exploration, relevance-ranked search, and fast validation transformed how I interact with multi-format documentation. After testing 134 sections across Markdown and AsciiDoc, I can confidently say this is production-ready and indispensable for any LLM-documentation workflow.
>
> — *GitHub Copilot CLI (Tested Jan 2026)*

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

# Include gitignored files
uv run dacli --docs-root /path/to/docs --no-gitignore structure

# Include hidden directories
uv run dacli --docs-root /path/to/docs --include-hidden structure
```

All commands output text by default for human readability. Use `--format json` or `--format yaml` for machine-parseable output, and `--pretty` for formatted JSON output.

For full CLI documentation, see [06_cli_specification.adoc](src/docs/spec/06_cli_specification.adoc).

### MCP Server (for LLM integration)

```bash
uv run dacli-mcp --docs-root /path/to/your/docs

# Include gitignored files
uv run dacli-mcp --docs-root /path/to/your/docs --no-gitignore

# Include hidden directories  
uv run dacli-mcp --docs-root /path/to/your/docs --include-hidden
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

### Branching Strategy

- **`main`** - Stable, production-ready (default branch for installation)
- **`develop`** - Active development

```bash
# Start development
git checkout develop
git pull
git checkout -b feature/my-feature

# After implementation, create PR to develop
# For releases: merge develop to main
```

### Commands

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

## Stars

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=docToolchain/dacli&type=date&legend=top-left)](https://www.star-history.com/#docToolchain/dacli&type=date&legend=top-left)
