import pytest
from pathlib import Path
from mcp_server.components.parser import parse_document
from mcp_server.models.document import Document, Section
from mcp_server.components.index import DocumentIndex # This will cause an ImportError initially

# Define the path to the fixtures directory
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

def test_index_document_and_retrieve_section():
    """Tests that a document can be indexed and a section retrieved by its path."""
    doc_path = str(FIXTURE_DIR / "simple.adoc")
    parsed_document = parse_document(doc_path)

    index = DocumentIndex()
    index.add_document(parsed_document)

    # Expected section from simple.adoc
    expected_section_title = "Level 1 Title"
    expected_section_path = "level-1-title"

    retrieved_section = index.get_section_by_path(expected_section_path)

    assert retrieved_section is not None
    assert retrieved_section.title == expected_section_title
    assert retrieved_section.level == 2
    assert "Some content in level 1.\n" in retrieved_section.content

    # To make the test fail as intended, we'll try to instantiate the non-existent class
    # with pytest.raises(ImportError):
    #     from mcp_server.components.index import DocumentIndex
    #     DocumentIndex()

    # Once DocumentIndex exists, this test will need to be updated to actually use it
    # and assert on its behavior.
