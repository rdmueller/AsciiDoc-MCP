# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Documentation Server - enables LLM interaction with large AsciiDoc/Markdown documentation projects through hierarchical, content-aware access via the Model Context Protocol (MCP).

**Current State:** Documentation and specification phase. Architecture (arc42) and API specs are complete; implementation pending.

## Technology Stack

- **Language:** Python 3.12+
- **Package Manager:** uv (https://github.com/astral-sh/uv)
- **Web Framework:** FastAPI
- **MCP SDK:** mcp[cli]

## Conventions

- Documentation, Issues, Pull-Requests etc. is always written in english
- use responsible-vibe-mcp wherever suitable

## Commands

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the server
uv run python -m mcp_server

# Add dependencies
uv add <package-name>
uv add --dev <package-name>

# Run tests
uv run pytest

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

- **Section:** Hierarchical document section with path, title, level, location
- **SectionLocation:** File path + line range (start_line, end_line)
- **Element:** Typed content (code, table, image) with location

## Documentation Structure

```
src/docs/
├── arc42/           # Architecture documentation (arc42 template)
│   └── chapters/    # Individual architecture chapters
└── spec/            # Specifications
    ├── 01_use_cases.adoc          # Use cases with activity diagrams
    ├── 02_api_specification.adoc  # OpenAPI-style API spec
    ├── 03_acceptance_criteria.adoc # Gherkin scenarios
    └── 04_markdown_parser.adoc    # Markdown parser component spec
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

### AsciiDoc Parser
- Resolves `include::[]` directives recursively
- Tracks original file path and line numbers for every element
- Builds AST with source-map information

### Markdown Parser (GFM)
- Folder hierarchy = document structure (no includes)
- Sorting: `index.md`/`README.md` first, then alphabetic with numeric prefix support
- Extracts: headings (structure), code blocks, tables, images (as addressable blocks)
- YAML frontmatter support for metadata

