# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**dacli** (Documentation Access CLI) - Navigate and query large documentation projects. Supports AsciiDoc and Markdown with hierarchical, content-aware access. Available as CLI tool and MCP server for LLM integration.

Part of the [docToolchain](https://doctoolchain.org/) ecosystem.

**Current State:** Core implementation complete. AsciiDoc/Markdown parsers, Structure Index, CLI and MCP tools are working. Some tech-debt issues remain for advanced features.

## Technology Stack

- **Language:** Python 3.12+
- **Package Manager:** uv (https://github.com/astral-sh/uv)
- **MCP Framework:** FastMCP (https://github.com/jlowin/fastmcp)
- **MCP SDK:** mcp[cli]

## Fork-Based Development Workflow

Development happens on a fork to keep `upstream/main` stable for `uv tool install`.

**Git Remotes:**
- `origin` → your fork (for development)
- `upstream` → `docToolchain/dacli` (stable, production-ready)

**Branches:**
- `upstream/main` - Stable, production-ready. **Default branch** (used by `uv tool install`).
- Feature branches on fork - Use format `feature/description-issue-number` or `fix/description-issue-number`

**Workflow:**
1. Sync fork: `git fetch upstream`
2. Create feature branch: `git checkout -b feature/xyz upstream/main`
3. Implement changes with tests
4. Push to fork: `git push origin feature/xyz`
5. Create PR from fork to `upstream/main` (use `Fixes #123` in PR body)
6. CI runs on PR, review, then merge
7. Issues auto-close when merged to main

## Conventions

- Documentation, Issues, Pull-Requests etc. is always written in english
- use responsible-vibe-mcp wherever suitable

## Commands

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run CLI
uv run dacli --help

# Run MCP server
uv run dacli-mcp --docs-root /path/to/docs

# Add dependencies
uv add <package-name>
uv add --dev <package-name>

# Run tests
uv run pytest

# Run tests with HTML report
uv run pytest --html=report.html --self-contained-html

# Run single test
uv run pytest tests/path/to/test.py::test_function_name
```

## Architecture

### Core Design Principles

1. **In-Memory Index:** On startup, parse all docs and build in-memory structure index for fast lookups
2. **File System as Truth:** Stateless design - file system is the single source of truth, no database
3. **Atomic Writes:** File modifications use temp files + backup strategy (ADR-004)

### Components (see `src/docs/arc42/chapters/05_building_block_view.adoc`)

| Component | Responsibility |
|-----------|---------------|
| API Endpoints | FastAPI routes, request validation |
| Document Service | Business logic for navigation/manipulation |
| Document Parser | Parse AsciiDoc/Markdown, resolve includes, build AST with line numbers |
| Structure Index | In-memory hierarchical structure for fast lookups |
| File System Handler | Atomic read/write operations |
| Search Service | Full-text search across indexed content |
| Validation Service | Structure validation, circular include detection |

### Key Data Models

- **Section:** Hierarchical document section with path (dot-notation), title, level, location
- **SourceLocation:** File path + line range (line, end_line, resolved_from for includes)
- **Element:** Typed content (code, table, image, list, plantuml, admonition) with location and index

### Path Format Convention

Section paths use dot-notation without document title prefix:
- Level 0 (document title): empty path `""`
- Level 1 (chapters): slug only, e.g., `"introduction"`
- Level 2+ (nested): parent.slug, e.g., `"introduction.goals"`

## Documentation Structure

```
src/docs/
├── 50-user-manual/  # User documentation
│   ├── index.adoc           # User manual index
│   ├── 10-installation.adoc # Installation guide
│   ├── 20-mcp-tools.adoc    # MCP tools reference
│   └── 50-tutorial.adoc     # CLI tutorial
├── arc42/           # Architecture documentation (arc42 template)
│   └── chapters/    # Individual architecture chapters
└── spec/            # Specifications
    ├── 01_use_cases.adoc          # Use cases with activity diagrams
    ├── 02_api_specification.adoc  # OpenAPI-style API spec
    ├── 03_acceptance_criteria.adoc # Gherkin scenarios
    ├── 04_markdown_parser.adoc    # Markdown parser component spec
    └── 06_cli_specification.adoc  # CLI interface specification
```

## Specification Conventions

### Use Cases (`01_use_cases.adoc`)
- PlantUML Activity Diagrams for each use case
- Structure: Akteure, Vorbedingungen, Ablauf, Nachbedingungen, Fehlerszenarien

### API Specification (`02_api_specification.adoc`)
- OpenAPI-style in AsciiDoc format
- Data models as JSON schemas with descriptions
- Endpoints grouped by API category (Navigation, Content Access, Manipulation, Meta-Information)

### Acceptance Criteria (`03_acceptance_criteria.adoc`)
- Gherkin format (Given-When-Then)
- Grouped by feature/use case
- German language

### Component Specifications (e.g., `04_markdown_parser.adoc`)
- Scope and limitations (what it does NOT do)
- Data models as Python dataclasses
- Acceptance criteria with Gherkin scenarios
- Interface definition

### Architecture Decision Records (ADRs)
- **Nygard format**: Status, Context, Decision, Consequences
- **Pugh Matrix** for each decision comparing alternatives
- Located in `src/docs/arc42/chapters/09_architecture_decisions.adoc`

## Key Architecture Decisions (ADRs)

Located in `src/docs/arc42/chapters/09_architecture_decisions.adoc`:

- **ADR-001:** File system as single source of truth (no database)
- **ADR-002:** In-memory index for performance
- **ADR-003:** Python/FastAPI stack
- **ADR-004:** Atomic writes via temporary files
- **ADR-005:** Custom parser for include resolution and source mapping
- **ADR-006:** uv for Python package management

## Parser Specifics

### AsciiDoc Structure Parser (`AsciidocStructureParser`)
- Resolves `include::[]` directives recursively
- Tracks original file path and line numbers for every element
- Builds AST with source-map information
- Detects circular includes

### Markdown Structure Parser (`MarkdownStructureParser`)
- Folder hierarchy = document structure (no includes)
- Sorting: `index.md`/`README.md` first, then alphabetic with numeric prefix support
- Extracts: headings (structure), code blocks (with content), tables, images
- YAML frontmatter support for metadata

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_structure` | Get hierarchical document structure |
| `get_section` | Read content of a specific section |
| `get_sections_at_level` | Get all sections at a nesting level |
| `search` | Full-text search across documentation |
| `get_elements` | Get code blocks, tables, images, etc. |
| `get_metadata` | Get project or section metadata |
| `validate_structure` | Validate documentation structure |
| `update_section` | Update section content (with optimistic locking) |
| `insert_content` | Insert content before/after sections |

For detailed tool documentation, see `src/docs/50-user-manual/`.

