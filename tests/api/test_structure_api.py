from fastapi.testclient import TestClient
from mcp_server.main import app
from pathlib import Path

# Define the path to the fixtures directory
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

def test_get_structure_endpoint(monkeypatch): # Added monkeypatch
    """
    Tests the /get_structure endpoint to ensure it returns the document hierarchy.
    """
    # Set the environment variable for the test
    monkeypatch.setenv("MCP_DOC_ROOT", str(FIXTURE_DIR))

    # Use TestClient within a 'with' statement to ensure startup/shutdown events are run
    with TestClient(app) as client:
        response = client.get("/get_structure")

        assert response.status_code == 200
        data = response.json()

        # Expected structure from simple.adoc
        # == Level 1 Title
        # === Level 2 Title
        # == Another Level 1 Title
        assert isinstance(data, list)
        assert len(data) == 3 # Expecting 3 sections from simple.adoc and include_main.adoc

        # Check first top-level section (from simple.adoc)
        assert data[0]["title"] == "Level 1 Title"
        assert data[0]["level"] == 2
        assert len(data[0]["subsections"]) == 1
        assert data[0]["subsections"][0]["title"] == "Level 2 Title"
        assert data[0]["subsections"][0]["level"] == 3

        # Check second top-level section (from simple.adoc)
        assert data[1]["title"] == "Another Level 1 Title"
        assert data[1]["level"] == 2
        assert len(data[1]["subsections"]) == 0

        # Check third top-level section (from include_main.adoc)
        assert data[2]["title"] == "Main Document Section"
        assert data[2]["level"] == 2
        assert len(data[2]["subsections"]) == 1 # Corrected: Expect 1 subsection
        assert data[2]["subsections"][0]["title"] == "Included Section" # Added check for subsection
        assert data[2]["subsections"][0]["level"] == 3 # Added check for subsection level

def test_get_section_endpoint(monkeypatch):
    """Tests the /get_section endpoint to retrieve a specific section by path."""
    monkeypatch.setenv("MCP_DOC_ROOT", str(FIXTURE_DIR))

    with TestClient(app) as client:
        # Test with a top-level section
        response = client.get("/get_section?path=level-1-title")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Level 1 Title"
        assert data["level"] == 2
        assert "Some content in level 1.\n" in data["content"]
        assert len(data["subsections"]) == 1

        # Test with a subsection
        response = client.get("/get_section?path=level-1-title/level-2-title")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Level 2 Title"
        assert data["level"] == 3
        assert "Some content in level 2.\n" in data["content"]
        assert len(data["subsections"]) == 0

        # Test with a non-existent path
        response = client.get("/get_section?path=non-existent-section")
        assert response.status_code == 404

def test_search_content_endpoint(monkeypatch):
    """Tests the /search_content endpoint to retrieve sections matching a query."""
    monkeypatch.setenv("MCP_DOC_ROOT", str(FIXTURE_DIR))

    with TestClient(app) as client:
        # Test with a query that should find results
        response = client.get("/search_content?query=content")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any("Level 1 Title" in s["title"] for s in data)
        assert any("Level 2 Title" in s["title"] for s in data)

        # Test with a query that should find no results
        response = client.get("/search_content?query=nonexistentword")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

