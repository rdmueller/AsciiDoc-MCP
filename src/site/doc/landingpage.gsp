<div class="row flex-xl-nowrap">
    <main class="col-12 col-md-12 col-xl-12 pl-md-12" role="main">
        <div class="bg-light p-5 rounded">
            <h1>MCP Documentation Server</h1>
            <p class="lead">
                Enable LLM interaction with large AsciiDoc and Markdown documentation projects through hierarchical, content-aware access via the Model Context Protocol (MCP).
            </p>
            <p>
                The MCP Documentation Server provides a powerful bridge between Large Language Models and your documentation.
                It parses your docs, builds an in-memory index, and exposes 9 MCP tools for navigation, search, and manipulation.
            </p>
            <p>
                <a href="https://github.com/rdmueller/AsciiDoc-MCP" class="btn btn-primary">View on GitHub</a>
                <a href="arc42/arc42.html" class="btn btn-outline-secondary">Architecture Documentation</a>
            </p>
        </div>

        <div class="row row-cols-1 row-cols-md-3 mb-3 text-center">
            <div class="col">
                <div class="card mb-4 shadow-sm">
                    <div class="card-header">
                        <h4 class="my-0 fw-normal">Hierarchical Navigation</h4>
                    </div>
                    <div class="card-body">
                        Browse documentation structure with configurable depth. Navigate chapters, sections, and subsections using intuitive dot-notation paths.
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="card mb-4 shadow-sm">
                    <div class="card-header">
                        <h4 class="my-0 fw-normal">Full-Text Search</h4>
                    </div>
                    <div class="card-body">
                        Search across all indexed documentation content. Find relevant sections quickly with scoped searches and relevance scoring.
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="card mb-4 shadow-sm">
                    <div class="card-header">
                        <h4 class="my-0 fw-normal">Document Manipulation</h4>
                    </div>
                    <div class="card-body">
                        Update sections and insert new content with optimistic locking support. Validate documentation structure for orphaned files and broken includes.
                    </div>
                </div>
            </div>
        </div>

        <div class="row row-cols-1 row-cols-md-2 mb-3">
            <div class="col">
                <div class="card mb-4 shadow-sm">
                    <div class="card-header">
                        <h4 class="my-0 fw-normal">Quick Start</h4>
                    </div>
                    <div class="card-body">
                        <pre><code># Clone and install
git clone https://github.com/rdmueller/AsciiDoc-MCP.git
cd AsciiDoc-MCP
uv sync

# Run the server
uv run python -m mcp_server --docs-root /path/to/docs</code></pre>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="card mb-4 shadow-sm">
                    <div class="card-header">
                        <h4 class="my-0 fw-normal">CLI for LLMs</h4>
                    </div>
                    <div class="card-body">
                        <pre><code># Install globally
uv tool install .

# Get document structure
dacli --docs-root /path/to/docs structure

# Search documentation
dacli search "authentication"</code></pre>
                    </div>
                </div>
            </div>
        </div>
    </main>

</div>
