from fastapi import FastAPI, HTTPException
from mcp_server.models.document import Document, Section
from mcp_server.components.parser import parse_document
from mcp_server.components.index import DocumentIndex
from pathlib import Path
from typing import List
import os
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__) # Moved to top

document_index: DocumentIndex = None # Now after logger

@asynccontextmanager # New decorator
async def lifespan(app: FastAPI): # New function signature
    global document_index
    document_index = DocumentIndex()
    
    # Get document root from environment variable or default to 'tests/fixtures'
    doc_root = Path(os.getenv("MCP_DOC_ROOT", "tests/fixtures"))

    # Explicitly list main documents for indexing
    main_docs_to_index = [
        doc_root / "simple.adoc",
        doc_root / "include_main.adoc",
        doc_root / "empty.adoc",
        doc_root / "no_sections.adoc",
    ]

    for doc_file in main_docs_to_index:
        try:
            parsed_doc = parse_document(str(doc_file))
            document_index.add_document(parsed_doc)
        except Exception as e:
            print(f"Error parsing {doc_file}: {e}")
    
    yield # This is where the application starts serving requests

    # Cleanup code can go here if needed for shutdown events
    logger.info("Application shutdown event.") # Changed print to logger.info


app = FastAPI(
    title="MCP Documentation Server",
    version="1.0.0",
    lifespan=lifespan # New argument
)

@app.get("/")
def read_root():
    """Root endpoint providing a welcome message."""
    return {"message": "Welcome to the MCP Documentation Server!"}

@app.get("/parse/", response_model=Document)
def parse_file(filepath: str):
    """
    Parses a single AsciiDoc file and returns its structure.
    """
    try:
        document = parse_document(filepath)
        return document
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/get_structure", response_model=List[Section])
def get_structure():
    """
    Returns the top-level structure of all indexed documents.
    """
    if document_index is None:
        raise HTTPException(status_code=503, detail="Document index not initialized.")
    
    # Return all top-level sections from the index
    return document_index.get_all_top_level_sections()

@app.get("/get_section", response_model=Section)
def get_section(path: str):
    """
    Retrieves a specific section by its hierarchical path.
    """
    if document_index is None:
        raise HTTPException(status_code=503, detail="Document index not initialized.")
    
    section = document_index.get_section_by_path(path)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Section not found: {path}")
    
    return section

@app.get("/search_content", response_model=List[Section])
def search_content(query: str):
    """
    Searches for sections whose title or content contains the query string.
    """
    if document_index is None:
        raise HTTPException(status_code=503, detail="Document index not initialized.")
    
    matching_sections = document_index.search_sections(query)
    return matching_sections
