"""FastAPI application factory.

Creates and configures the FastAPI application with all routers.
"""

from fastapi import FastAPI

from dacli import __version__
from dacli.api import content, manipulation, navigation
from dacli.structure_index import StructureIndex


def create_app(index: StructureIndex | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        index: Optional pre-configured StructureIndex.
               If None, the index must be set later.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="MCP Documentation Server",
        description="LLM interaction with large documentation projects via MCP",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Set the index for routers
    if index is not None:
        navigation.set_index(index)
        content.set_index(index)
        manipulation.set_index(index)

    # Include routers
    app.include_router(navigation.router)
    app.include_router(content.router)
    app.include_router(manipulation.router)

    return app
