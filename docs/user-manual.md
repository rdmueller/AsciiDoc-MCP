# MCP Documentation Server - User Manual

This manual provides detailed documentation for all available MCP tools, configuration options, and practical examples.

## Table of Contents

- [Configuration](#configuration)
- [CLI Interface (dacli)](#cli-interface-dacli)
- [Navigation Tools](#navigation-tools)
- [Content Access Tools](#content-access-tools)
- [Search](#search)
- [Document Manipulation](#document-manipulation)
- [Meta-Information](#meta-information)
- [Example Workflows](#example-workflows)

---

## Configuration

### Claude Desktop

Add the server to your Claude Desktop configuration:

**Linux:** `~/.config/claude-desktop/config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "asciidoc-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/AsciiDoc-MCP",
        "python", "-m", "mcp_server",
        "--docs-root", "/path/to/your/documentation"
      ]
    }
  }
}
```

### Amazon Q CLI / Kiro

```json
{
  "mcpServers": {
    "asciidoc-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/AsciiDoc-MCP",
        "python", "-m", "mcp_server",
        "--docs-root", "/path/to/documentation"
      ]
    }
  }
}
```

### Command Line Options

```bash
uv run python -m mcp_server [OPTIONS]

Options:
  --docs-root PATH    Root directory containing documentation files
  --help              Show help message
```

---

## CLI Interface (dacli)

For LLMs without MCP support, all tools are available via the `dacli` command-line interface.

### Installation

```bash
# dacli is included with the server
uv sync
```

### Global Options

```bash
dacli [OPTIONS] COMMAND [ARGS]

Options:
  --docs-root PATH         Documentation root directory (default: current directory)
  --format [json|yaml|text]  Output format (default: json)
  --pretty                 Pretty-print output for human readability
  --version                Show version
  --help                   Show help
```

### Available Commands

| Command | Description | MCP Equivalent |
|---------|-------------|----------------|
| `structure` | Get document structure | `get_structure` |
| `section PATH` | Read section content | `get_section` |
| `sections-at-level LEVEL` | Get sections at level | `get_sections_at_level` |
| `search QUERY` | Search documentation | `search` |
| `elements` | Get code/tables/images | `get_elements` |
| `metadata [PATH]` | Get metadata | `get_metadata` |
| `validate` | Validate structure | `validate_structure` |
| `update PATH` | Update section | `update_section` |
| `insert PATH` | Insert content | `insert_content` |

### CLI Examples

```bash
# Get structure (max depth 2, pretty output)
dacli --docs-root /path/to/docs --pretty structure --max-depth 2

# Read a section
dacli section introduction.goals

# Search with scope
dacli search "authentication" --scope security --max-results 10

# Get all code blocks
dacli elements --type code

# Get project metadata
dacli metadata

# Get section metadata
dacli metadata architecture.decisions

# Validate structure
dacli validate

# Update a section
dacli update api.endpoints --content "New content..."

# Insert content after a section
dacli insert architecture --position after --content "== New Section\n\nContent..."
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Path not found |
| 4 | Validation error |
| 5 | Write error |

### LLM Integration Example

```bash
# An LLM can use dacli via bash tools:

# Get structure
structure=$(dacli structure --max-depth 2 --docs-root /project/docs)

# Search and extract paths
results=$(dacli search "database" | jq '.results[].path')

# Read a section
content=$(dacli section architecture.decisions)

# Update documentation
dacli update api.endpoints --content "Updated API documentation..."
```

---

## Navigation Tools

### get_structure

Get the hierarchical document structure.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_depth` | int \| null | null | Maximum depth to return. Use 1 for top-level only. |

**Returns:**
```json
{
  "sections": [
    {
      "path": "introduction",
      "title": "Introduction",
      "level": 1,
      "children": [
        {
          "path": "introduction.goals",
          "title": "Goals",
          "level": 2,
          "children": []
        }
      ]
    }
  ],
  "total_sections": 15
}
```

**Example:**
```
get_structure(max_depth=2)
```

---

### get_sections_at_level

Get all sections at a specific nesting level.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `level` | int | Nesting level (1 = chapters, 2 = sections, etc.) |

**Returns:**
```json
{
  "level": 1,
  "sections": [
    {"path": "introduction", "title": "Introduction"},
    {"path": "architecture", "title": "Architecture"}
  ],
  "count": 2
}
```

---

## Content Access Tools

### get_section

Read the content of a specific section.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Hierarchical path using dot notation (e.g., `introduction.goals`) |

**Returns:**
```json
{
  "path": "introduction.goals",
  "title": "Goals",
  "content": "== Goals\n\nThis section describes...",
  "location": {
    "file": "/docs/chapters/01_introduction.adoc",
    "start_line": 15,
    "end_line": 42
  },
  "format": "asciidoc"
}
```

**Error Response (with suggestions):**
```json
{
  "error": {
    "code": "PATH_NOT_FOUND",
    "message": "Section 'intro' not found",
    "details": {
      "requested_path": "intro",
      "suggestions": ["introduction", "intro-page"]
    }
  }
}
```

---

### get_elements

Get code blocks, tables, images, and other elements.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `element_type` | string \| null | null | Filter by type: `code`, `table`, `image`, `diagram`, `list` |
| `section_path` | string \| null | null | Filter by section path |

**Returns:**
```json
{
  "elements": [
    {
      "type": "code",
      "location": {
        "file": "/docs/example.adoc",
        "line": 25
      },
      "preview": "[python] def hello()...",
      "section_path": "examples.python"
    }
  ],
  "count": 5
}
```

**Example - Get all code blocks:**
```
get_elements(element_type="code")
```

**Example - Get elements in a specific section:**
```
get_elements(section_path="architecture.components")
```

---

## Search

### search

Full-text search across documentation.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | - | Search query (case-insensitive) |
| `scope` | string \| null | null | Path prefix to limit search scope |
| `max_results` | int | 50 | Maximum results to return |

**Returns:**
```json
{
  "query": "authentication",
  "results": [
    {
      "path": "security.authentication",
      "line": 45,
      "context": "...implements OAuth2 authentication...",
      "score": 0.95
    }
  ],
  "total_results": 3
}
```

**Example - Search in specific section:**
```
search(query="database", scope="architecture")
```

---

## Document Manipulation

### update_section

Update the content of a section with optimistic locking support.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | - | Section path using dot notation |
| `content` | string | - | New section content |
| `preserve_title` | bool | true | Keep original title if content doesn't include one |
| `expected_hash` | string \| null | null | Hash for optimistic locking |

**Returns:**
```json
{
  "success": true,
  "path": "introduction.goals",
  "location": {
    "file": "/docs/01_intro.adoc",
    "line": 15
  },
  "previous_hash": "a1b2c3d4",
  "new_hash": "e5f6g7h8"
}
```

**Optimistic Locking Workflow:**
1. Read section with `get_section` - note the content
2. Compute or receive hash of current content
3. Call `update_section` with `expected_hash`
4. If hash mismatch, update fails with conflict error

---

### insert_content

Insert content relative to a section.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Reference section path |
| `position` | string | `before`, `after`, or `append` |
| `content` | string | Content to insert |

**Position Options:**
- `before` - Insert before section start
- `after` - Insert after section end
- `append` - Append at end of section (before children)

**Returns:**
```json
{
  "success": true,
  "inserted_at": {
    "file": "/docs/chapter.adoc",
    "line": 50
  },
  "previous_hash": "a1b2c3d4",
  "new_hash": "e5f6g7h8"
}
```

---

## Meta-Information

### get_metadata

Get project or section metadata.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string \| null | null | Section path, or null for project metadata |

**Project Metadata (no path):**
```json
{
  "path": null,
  "total_files": 15,
  "total_sections": 87,
  "total_words": 12450,
  "last_modified": "2026-01-20T14:30:00+00:00",
  "formats": ["asciidoc", "markdown"]
}
```

**Section Metadata (with path):**
```json
{
  "path": "architecture.decisions",
  "title": "Architecture Decisions",
  "file": "/docs/chapters/09_decisions.adoc",
  "word_count": 2340,
  "last_modified": "2026-01-19T10:15:00+00:00",
  "subsection_count": 5
}
```

---

### validate_structure

Validate the documentation structure.

**Parameters:** None

**Returns:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "type": "orphaned_file",
      "path": "chapters/unused.adoc",
      "message": "File is not included in any document"
    }
  ],
  "validation_time_ms": 120
}
```

**Error Types:**
- `unresolved_include` - Include directive points to missing file
- `circular_include` - Circular include chain detected

**Warning Types:**
- `orphaned_file` - File exists but is not referenced

---

## Example Workflows

### 1. Exploring a New Documentation Project

```
# Get high-level structure
get_structure(max_depth=1)

# Get project statistics
get_metadata()

# Browse chapters
get_sections_at_level(level=1)

# Read a specific chapter
get_section(path="architecture")
```

### 2. Finding and Extracting Code Examples

```
# Find all code blocks
get_elements(element_type="code")

# Find code in specific section
get_elements(element_type="code", section_path="examples")

# Search for specific language
search(query="python")
```

### 3. Updating Documentation

```
# Read current content
get_section(path="api.endpoints")

# Update with new content (preserving title)
update_section(
  path="api.endpoints",
  content="New endpoint documentation...",
  preserve_title=true
)

# Add a new section after existing one
insert_content(
  path="api.endpoints",
  position="after",
  content="== New Endpoint\n\nDescription..."
)
```

### 4. Validating Documentation Quality

```
# Check for structural issues
validate_structure()

# Get word counts for sections
get_metadata(path="introduction")
get_metadata(path="architecture")
```

---

## Path Format

Paths use dot notation without document title prefix:

| Level | Example Path |
|-------|-------------|
| Document root | `""` (empty) |
| Chapter | `introduction` |
| Section | `introduction.goals` |
| Subsection | `introduction.goals.performance` |

Paths are case-sensitive and derived from section titles (slugified).
