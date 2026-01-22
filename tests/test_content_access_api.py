"""Tests for Content Access API endpoints.

These tests verify the Content Access API endpoints:
- POST /api/v1/search
- GET /api/v1/elements
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dacli.api.app import create_app
from dacli.models import Document, Element, Section, SourceLocation
from dacli.structure_index import StructureIndex


@pytest.fixture
def sample_index() -> StructureIndex:
    """Create a sample index with test data for content access."""
    index = StructureIndex()
    doc = Document(
        file_path=Path("docs/test.adoc"),
        title="Test Documentation",
        sections=[
            Section(
                title="Introduction",
                level=1,
                path="/introduction",
                source_location=SourceLocation(file=Path("docs/intro.adoc"), line=1),
                children=[
                    Section(
                        title="Goals and Performance",
                        level=2,
                        path="/introduction/goals",
                        source_location=SourceLocation(
                            file=Path("docs/intro.adoc"), line=10
                        ),
                    ),
                ],
            ),
            Section(
                title="Quality Attributes",
                level=1,
                path="/quality",
                source_location=SourceLocation(file=Path("docs/quality.adoc"), line=1),
                children=[
                    Section(
                        title="Performance Requirements",
                        level=2,
                        path="/quality/performance",
                        source_location=SourceLocation(
                            file=Path("docs/quality.adoc"), line=15
                        ),
                    ),
                    Section(
                        title="Security",
                        level=2,
                        path="/quality/security",
                        source_location=SourceLocation(
                            file=Path("docs/quality.adoc"), line=30
                        ),
                    ),
                ],
            ),
            Section(
                title="Decisions",
                level=1,
                path="/decisions",
                source_location=SourceLocation(
                    file=Path("docs/decisions.adoc"), line=1
                ),
                children=[
                    Section(
                        title="ADR-004 Atomic Write Operations",
                        level=2,
                        path="/decisions/adr-004",
                        source_location=SourceLocation(
                            file=Path("docs/decisions.adoc"), line=20
                        ),
                    ),
                ],
            ),
        ],
        elements=[
            Element(
                type="code",
                source_location=SourceLocation(file=Path("docs/intro.adoc"), line=25),
                attributes={"language": "python"},
                parent_section="/introduction/goals",
            ),
            Element(
                type="code",
                source_location=SourceLocation(file=Path("docs/quality.adoc"), line=50),
                attributes={"language": "java"},
                parent_section="/quality/performance",
            ),
            Element(
                type="table",
                source_location=SourceLocation(file=Path("docs/quality.adoc"), line=60),
                attributes={},
                parent_section="/quality/performance",
            ),
            Element(
                type="table",
                source_location=SourceLocation(file=Path("docs/quality.adoc"), line=80),
                attributes={},
                parent_section="/quality/security",
            ),
            Element(
                type="plantuml",
                source_location=SourceLocation(
                    file=Path("docs/decisions.adoc"), line=30
                ),
                attributes={"format": "svg", "name": "adr-diagram"},
                parent_section="/decisions/adr-004",
            ),
            Element(
                type="image",
                source_location=SourceLocation(file=Path("docs/intro.adoc"), line=40),
                attributes={"alt": "Architecture overview"},
                parent_section="/introduction",
            ),
        ],
    )
    index.build_from_documents([doc])
    return index


@pytest.fixture
def client(sample_index: StructureIndex) -> TestClient:
    """Create a test client with the sample index."""
    app = create_app(sample_index)
    return TestClient(app)


# =============================================================================
# POST /search Tests (UC-04)
# =============================================================================


class TestSearchEndpoint:
    """Tests for POST /api/v1/search endpoint."""

    def test_search_returns_200(self, client: TestClient):
        """POST /search returns 200."""
        response = client.post("/api/v1/search", json={"query": "test"})
        assert response.status_code == 200

    def test_search_with_matches(self, client: TestClient):
        """AC-UC04-01: Successful search with matches."""
        response = client.post("/api/v1/search", json={"query": "Performance"})
        data = response.json()

        assert response.status_code == 200
        assert "results" in data
        assert "total_results" in data
        assert data["total_results"] > 0
        assert data["query"] == "Performance"

        # Each result has required fields
        for result in data["results"]:
            assert "path" in result
            assert "line" in result
            assert "context" in result
            assert "score" in result
            assert 0 <= result["score"] <= 1

    def test_search_no_matches(self, client: TestClient):
        """AC-UC04-02: Search without matches returns empty list."""
        response = client.post(
            "/api/v1/search", json={"query": "xyznonexistentterm"}
        )
        data = response.json()

        assert response.status_code == 200
        assert data["results"] == []
        assert data["total_results"] == 0

    def test_search_with_scope(self, client: TestClient):
        """AC-UC04-03: Search with scope restriction."""
        response = client.post(
            "/api/v1/search",
            json={"query": "Performance", "scope": "/quality"},
        )
        data = response.json()

        assert response.status_code == 200
        # All results should be within /quality scope
        for result in data["results"]:
            assert result["path"].startswith("/quality")

    def test_search_case_sensitive(self, client: TestClient):
        """AC-UC04-04: Case-sensitive search."""
        # First, verify there's a match with case-insensitive search
        response = client.post(
            "/api/v1/search",
            json={"query": "performance", "case_sensitive": False},
        )
        assert response.json()["total_results"] > 0

        # Now do case-sensitive search - "performance" lowercase
        # shouldn't match "Performance" in titles
        response = client.post(
            "/api/v1/search",
            json={"query": "performance", "case_sensitive": True},
        )
        # The section titles have "Performance" with capital P
        # so lowercase "performance" shouldn't match
        data = response.json()
        assert response.status_code == 200
        # Check that lowercase didn't match capitalized titles
        assert data["total_results"] == 0
        assert data["results"] == []

    def test_search_max_results(self, client: TestClient):
        """AC-UC04-05: Search with result limit."""
        # Search for common term
        response = client.post(
            "/api/v1/search",
            json={"query": "a", "max_results": 2},  # Common letter
        )
        data = response.json()

        assert response.status_code == 200
        assert len(data["results"]) <= 2

    def test_search_includes_search_time(self, client: TestClient):
        """Search response includes search_time_ms."""
        response = client.post("/api/v1/search", json={"query": "test"})
        data = response.json()

        assert "search_time_ms" in data
        assert isinstance(data["search_time_ms"], int)
        assert data["search_time_ms"] >= 0

    def test_search_results_sorted_by_score(self, client: TestClient):
        """Search results are sorted by score descending."""
        response = client.post(
            "/api/v1/search", json={"query": "Performance"}
        )
        data = response.json()

        if len(data["results"]) > 1:
            scores = [r["score"] for r in data["results"]]
            assert scores == sorted(scores, reverse=True)

    def test_search_empty_query_fails(self, client: TestClient):
        """Empty query returns validation error."""
        response = client.post("/api/v1/search", json={"query": ""})
        # Pydantic validation or custom validation should reject empty query
        # Status could be 400 or 422 depending on implementation
        assert response.status_code in [400, 422]


# =============================================================================
# GET /elements Tests (UC-05)
# =============================================================================


class TestElementsEndpoint:
    """Tests for GET /api/v1/elements endpoint."""

    def test_get_elements_returns_200(self, client: TestClient):
        """GET /elements returns 200 for valid type."""
        response = client.get("/api/v1/elements?type=code")
        assert response.status_code == 200

    def test_get_code_elements(self, client: TestClient):
        """AC-UC05-01: Get all code elements."""
        response = client.get("/api/v1/elements?type=code")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "code"
        assert data["count"] == 2  # Two code blocks in fixture
        assert len(data["elements"]) == 2

        # Each element has required fields
        for elem in data["elements"]:
            assert "type" in elem
            assert "path" in elem
            assert "location" in elem
            assert "file" in elem["location"]
            assert "start_line" in elem["location"]

    def test_get_table_elements(self, client: TestClient):
        """Get all table elements."""
        response = client.get("/api/v1/elements?type=table")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "table"
        assert data["count"] == 2  # Two tables in fixture

    def test_get_diagram_elements(self, client: TestClient):
        """Get diagram elements (mapped from plantuml)."""
        response = client.get("/api/v1/elements?type=diagram")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "diagram"
        # plantuml type should map to diagram
        assert data["count"] == 1

    def test_get_image_elements(self, client: TestClient):
        """Get image elements."""
        response = client.get("/api/v1/elements?type=image")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "image"
        assert data["count"] == 1

    def test_get_elements_with_path_filter(self, client: TestClient):
        """AC-UC05-02: Get elements filtered by section path."""
        response = client.get(
            "/api/v1/elements?type=table&path=/quality/performance"
        )
        data = response.json()

        assert response.status_code == 200
        assert data["count"] == 1  # Only one table in /quality/performance
        assert data["elements"][0]["path"] == "/quality/performance"

    def test_get_elements_invalid_type(self, client: TestClient):
        """AC-UC05-03: Invalid element type returns 400."""
        response = client.get("/api/v1/elements?type=charts")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_TYPE"
        assert "valid_types" in data["detail"]["error"]["details"]

    def test_get_elements_no_matches(self, client: TestClient):
        """AC-UC05-04: Element type without matches returns empty array."""
        response = client.get("/api/v1/elements?type=list")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "list"
        assert data["elements"] == []
        assert data["count"] == 0

    def test_get_elements_requires_type(self, client: TestClient):
        """Type parameter is required."""
        response = client.get("/api/v1/elements")
        assert response.status_code == 422  # Validation error

    def test_get_elements_includes_index(self, client: TestClient):
        """Elements include index field."""
        response = client.get("/api/v1/elements?type=code")
        data = response.json()

        for elem in data["elements"]:
            assert "index" in elem
            assert isinstance(elem["index"], int)


# =============================================================================
# Empty Index Tests
# =============================================================================


class TestEmptyIndex:
    """Tests for API behavior with empty index."""

    @pytest.fixture
    def empty_client(self) -> TestClient:
        """Create a test client with empty index."""
        index = StructureIndex()
        index.build_from_documents([])
        app = create_app(index)
        return TestClient(app)

    def test_empty_search_returns_200(self, empty_client: TestClient):
        """Empty index search returns 200 with no results."""
        response = empty_client.post("/api/v1/search", json={"query": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total_results"] == 0

    def test_empty_elements_returns_200(self, empty_client: TestClient):
        """Empty index elements returns 200 with empty list."""
        response = empty_client.get("/api/v1/elements?type=code")

        assert response.status_code == 200
        data = response.json()
        assert data["elements"] == []
        assert data["count"] == 0
