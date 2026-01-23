<div class="row flex-xl-nowrap">
    <main class="col-12 col-md-12 col-xl-12 pl-md-12" role="main">
        <!-- Hero Section with JTBD Focus -->
        <div class="p-5 rounded" style="background: linear-gradient(135deg, #1a365d 0%, #2d5a87 100%); color: white; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; font-weight: 700;">dacli</h1>
            <p class="lead" style="font-size: 1.4rem; opacity: 0.95;">
                Let your AI understand your documentation.
            </p>
            <p style="font-size: 1.1rem; opacity: 0.85; max-width: 700px;">
                Large documentation projects are hard for LLMs to navigate. dacli gives AI assistants structured access to your AsciiDoc and Markdown docs - so they can find, read, and update exactly what they need.
            </p>
            <p style="margin-top: 1.5rem;">
                <a href="https://github.com/docToolchain/dacli" class="btn btn-light btn-lg" style="font-weight: 600;">
                    Get Started
                </a>
                <a href="50-user-manual/index.html" class="btn btn-outline-light btn-lg" style="margin-left: 0.5rem;">
                    Documentation
                </a>
            </p>
        </div>

        <!-- Jobs to be Done Section -->
        <h2 style="text-align: center; margin-bottom: 2rem; color: #1a365d;">What can you accomplish?</h2>

        <div class="row row-cols-1 row-cols-md-2 mb-4">
            <div class="col mb-4">
                <div class="card h-100 shadow-sm border-0" style="border-left: 4px solid #2d5a87 !important;">
                    <div class="card-body">
                        <h4 class="card-title" style="color: #1a365d;">
                            <span style="font-size: 1.5rem; margin-right: 0.5rem;">&#128269;</span>
                            Find information instantly
                        </h4>
                        <p class="card-text">
                            "Where is the authentication logic documented?"<br>
                            Your AI assistant searches across all your docs and finds the exact section - no more manual searching through hundreds of files.
                        </p>
                    </div>
                </div>
            </div>
            <div class="col mb-4">
                <div class="card h-100 shadow-sm border-0" style="border-left: 4px solid #2d5a87 !important;">
                    <div class="card-body">
                        <h4 class="card-title" style="color: #1a365d;">
                            <span style="font-size: 1.5rem; margin-right: 0.5rem;">&#128506;</span>
                            Navigate complex structures
                        </h4>
                        <p class="card-text">
                            "Show me the architecture overview."<br>
                            dacli understands your document hierarchy. AI can browse chapters, sections, and subsections - just like a human would.
                        </p>
                    </div>
                </div>
            </div>
            <div class="col mb-4">
                <div class="card h-100 shadow-sm border-0" style="border-left: 4px solid #2d5a87 !important;">
                    <div class="card-body">
                        <h4 class="card-title" style="color: #1a365d;">
                            <span style="font-size: 1.5rem; margin-right: 0.5rem;">&#9997;</span>
                            Keep docs up-to-date
                        </h4>
                        <p class="card-text">
                            "Update the API documentation for the new endpoint."<br>
                            AI can read existing docs and make targeted updates - with optimistic locking to prevent conflicts.
                        </p>
                    </div>
                </div>
            </div>
            <div class="col mb-4">
                <div class="card h-100 shadow-sm border-0" style="border-left: 4px solid #2d5a87 !important;">
                    <div class="card-body">
                        <h4 class="card-title" style="color: #1a365d;">
                            <span style="font-size: 1.5rem; margin-right: 0.5rem;">&#128640;</span>
                            Works with your tools
                        </h4>
                        <p class="card-text">
                            Use as an MCP server with Claude Desktop, Cursor, or any MCP-compatible AI. Or use the CLI for LLMs that support shell commands.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- How it works -->
        <div class="bg-light p-4 rounded mb-4">
            <h3 style="color: #1a365d; margin-bottom: 1.5rem;">Two ways to connect</h3>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <div class="card h-100">
                        <div class="card-header" style="background-color: #1a365d; color: white;">
                            <h5 class="mb-0">MCP Server</h5>
                            <small>For Claude Desktop, Cursor & MCP clients</small>
                        </div>
                        <div class="card-body">
                            <pre style="background: #f8f9fa; padding: 1rem; border-radius: 4px; font-size: 0.85rem;"><code># Add to your MCP client config
{
  "mcpServers": {
    "dacli": {
      "command": "uvx",
      "args": ["dacli-mcp",
        "--docs-root", "/path/to/docs"]
    }
  }
}</code></pre>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-3">
                    <div class="card h-100">
                        <div class="card-header" style="background-color: #2d5a87; color: white;">
                            <h5 class="mb-0">CLI Tool</h5>
                            <small>For LLMs with shell access</small>
                        </div>
                        <div class="card-body">
                            <pre style="background: #f8f9fa; padding: 1rem; border-radius: 4px; font-size: 0.85rem;"><code># Install once
uv tool install dacli

# Then use anywhere
dacli --docs-root ./docs structure
dacli search "authentication"
dacli section api.endpoints</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Supported Formats -->
        <div class="text-center mb-4 p-4">
            <h4 style="color: #1a365d;">Supports your documentation format</h4>
            <p class="text-muted">
                <span style="font-size: 1.2rem; margin: 0 1rem;">&#128196; AsciiDoc</span>
                <span style="font-size: 1.2rem; margin: 0 1rem;">&#128221; Markdown</span>
            </p>
            <p class="text-muted">
                Including nested includes, code blocks, tables, images, and PlantUML diagrams.
            </p>
        </div>

        <!-- Social Proof -->
        <div class="mb-4 p-4">
            <h3 style="color: #1a365d; text-align: center; margin-bottom: 1.5rem;">What Others Say</h3>
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card shadow-sm border-0" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
                        <div class="card-body p-4">
                            <div style="text-align: center; margin-bottom: 1rem;">
                                <span style="font-size: 3rem; color: #2d5a87; opacity: 0.3;">&ldquo;</span>
                            </div>
                            <p style="font-size: 1.3rem; font-style: italic; color: #1a365d; text-align: center; margin-bottom: 1rem; line-height: 1.6;">
                                dacli is the missing tool between LLMs and Docs-as-Code.
                            </p>
                            <p style="color: #555; text-align: center; margin-bottom: 1rem;">
                                No more guessing line numbers, no more "which README do you mean?" questions.
                            </p>
                            <p style="text-align: center; margin-bottom: 1.5rem;">
                                <span style="background-color: #2d5a87; color: white; padding: 0.4rem 1rem; border-radius: 20px; font-weight: 600; font-size: 0.95rem;">
                                    &#10003; Ready for production use
                                </span>
                            </p>
                            <div style="text-align: center; border-top: 1px solid #dee2e6; padding-top: 1rem;">
                                <span style="font-size: 1.5rem;">&#129302;</span>
                                <p style="color: #1a365d; font-weight: 600; margin: 0.5rem 0 0 0;">Claude (Opus 4.5)</p>
                                <p style="color: #666; font-size: 0.85rem; margin: 0;">Independent Review</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- More testimonials coming soon -->
        </div>

        <!-- Call to Action -->
        <div class="text-center p-4 rounded" style="background-color: #f0f7ff;">
            <h3 style="color: #1a365d;">Ready to give your AI documentation superpowers?</h3>
            <p class="text-muted mb-3">Part of the <a href="https://doctoolchain.org" style="color: #2d5a87;">docToolchain</a> ecosystem.</p>
            <p>
                <a href="https://github.com/docToolchain/dacli" class="btn btn-primary btn-lg">View on GitHub</a>
                <a href="arc42/chapters/01_introduction_and_goals.html" class="btn btn-outline-secondary btn-lg">Architecture Docs</a>
            </p>
        </div>
    </main>
</div>
