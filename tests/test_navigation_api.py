"""Tests for Navigation API endpoints.

These tests verify the Navigation API endpoints:
- GET /api/v1/structure
- GET /api/v1/section/{path}
- GET /api/v1/sections
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dacli.api.app import create_app
from dacli.models import Document, Element, Section, SourceLocation
from dacli.structure_index import StructureIndex


@pytest.fixture
def sample_index() -> StructureIndex:
    """Create a sample index with test data."""
    index = StructureIndex()
    doc = Document(
        file_path=Path("docs/intro.adoc"),
        title="Test Documentation",
        sections=[
            Section(
                title="Introduction",
                level=1,
                path="/introduction",
                source_location=SourceLocation(file=Path("docs/intro.adoc"), line=1),
                children=[
                    Section(
                        title="Goals",
                        level=2,
                        path="/introduction/goals",
                        source_location=SourceLocation(
                            file=Path("docs/intro.adoc"), line=10
                        ),
                    ),
                    Section(
                        title="Scope",
                        level=2,
                        path="/introduction/scope",
                        source_location=SourceLocation(
                            file=Path("docs/intro.adoc"), line=20
                        ),
                    ),
                ],
            ),
            Section(
                title="Constraints",
                level=1,
                path="/constraints",
                source_location=SourceLocation(file=Path("docs/constraints.adoc"), line=1),
                children=[
                    Section(
                        title="Technical",
                        level=2,
                        path="/constraints/technical",
                        source_location=SourceLocation(
                            file=Path("docs/constraints.adoc"), line=15
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
        ],
    )
    index.build_from_documents([doc])
    return index


@pytest.fixture
def client(sample_index: StructureIndex) -> TestClient:
    """Create a test client with the sample index."""
    app = create_app(sample_index)
    return TestClient(app)


class TestGetStructure:
    """Tests for GET /api/v1/structure endpoint."""

    def test_get_structure_returns_200(self, client: TestClient):
        """AC-NAV-01: GET /structure returns 200."""
        response = client.get("/api/v1/structure")
        assert response.status_code == 200

    def test_get_structure_returns_all_sections(self, client: TestClient):
        """AC-NAV-01: Response contains all sections."""
        response = client.get("/api/v1/structure")
        data = response.json()

        assert "sections" in data
        assert "total_sections" in data
        assert data["total_sections"] == 5  # 2 level-1 + 3 level-2

    def test_get_structure_is_hierarchical(self, client: TestClient):
        """AC-NAV-01: Structure is hierarchically nested."""
        response = client.get("/api/v1/structure")
        data = response.json()

        # Check top-level sections
        assert len(data["sections"]) == 2
        assert data["sections"][0]["path"] == "/introduction"
        assert data["sections"][0]["title"] == "Introduction"

        # Check nested children
        intro = data["sections"][0]
        assert "children" in intro
        assert len(intro["children"]) == 2
        assert intro["children"][0]["path"] == "/introduction/goals"

    def test_get_structure_with_max_depth_1(self, client: TestClient):
        """AC-NAV-02: max_depth=1 returns only level 1 sections."""
        response = client.get("/api/v1/structure?max_depth=1")
        data = response.json()

        assert response.status_code == 200
        assert len(data["sections"]) == 2

        # Children should be empty due to max_depth
        for section in data["sections"]:
            assert section["children"] == []

    def test_get_structure_with_max_depth_2(self, client: TestClient):
        """max_depth=2 returns levels 1 and 2."""
        response = client.get("/api/v1/structure?max_depth=2")
        data = response.json()

        assert response.status_code == 200

        # Level 1 sections should have children
        intro = data["sections"][0]
        assert len(intro["children"]) == 2

        # Level 2 children should have empty children (no level 3)
        for child in intro["children"]:
            assert child["children"] == []

    def test_get_structure_section_has_location(self, client: TestClient):
        """Sections include location information."""
        response = client.get("/api/v1/structure")
        data = response.json()

        section = data["sections"][0]
        assert "location" in section
        assert "file" in section["location"]
        assert "line" in section["location"]


class TestGetSection:
    """Tests for GET /api/v1/section/{path} endpoint."""

    def test_get_section_returns_200(self, client: TestClient):
        """AC-NAV-03: GET /section/{path} returns 200 for existing section."""
        response = client.get("/api/v1/section/introduction")
        assert response.status_code == 200

    def test_get_section_returns_section_data(self, client: TestClient):
        """AC-NAV-03: Response contains section data."""
        response = client.get("/api/v1/section/introduction")
        data = response.json()

        assert data["path"] == "/introduction"
        assert data["title"] == "Introduction"
        assert data["level"] == 1
        assert "location" in data

    def test_get_section_with_nested_path(self, client: TestClient):
        """Nested paths work correctly."""
        response = client.get("/api/v1/section/introduction/goals")
        data = response.json()

        assert response.status_code == 200
        assert data["path"] == "/introduction/goals"
        assert data["title"] == "Goals"
        assert data["level"] == 2

    def test_get_section_returns_404_for_nonexistent(self, client: TestClient):
        """AC-NAV-04: Returns 404 for non-existent path."""
        response = client.get("/api/v1/section/nonexistent/path")

        assert response.status_code == 404
        data = response.json()
        # FastAPI wraps HTTPException detail in "detail" key
        assert data["detail"]["error"]["code"] == "PATH_NOT_FOUND"

    def test_get_section_404_includes_message(self, client: TestClient):
        """AC-NAV-04: 404 includes error message with path."""
        response = client.get("/api/v1/section/nonexistent")
        data = response.json()

        assert "nonexistent" in data["detail"]["error"]["message"]

    def test_get_section_location_has_file_and_line(self, client: TestClient):
        """Location includes file and line information."""
        response = client.get("/api/v1/section/introduction")
        data = response.json()

        assert data["location"]["file"] == "docs/intro.adoc"
        assert data["location"]["line"] == 1


class TestGetSections:
    """Tests for GET /api/v1/sections endpoint."""

    def test_get_sections_at_level_1(self, client: TestClient):
        """AC-NAV-05: GET /sections?level=1 returns level 1 sections."""
        response = client.get("/api/v1/sections?level=1")

        assert response.status_code == 200
        data = response.json()

        assert data["level"] == 1
        assert "sections" in data
        assert "count" in data
        assert data["count"] == 2

        # All sections should be level 1
        for section in data["sections"]:
            assert section["path"] in ["/introduction", "/constraints"]

    def test_get_sections_at_level_2(self, client: TestClient):
        """GET /sections?level=2 returns level 2 sections."""
        response = client.get("/api/v1/sections?level=2")

        assert response.status_code == 200
        data = response.json()

        assert data["level"] == 2
        assert data["count"] == 3  # goals, scope, technical

    def test_get_sections_returns_empty_for_nonexistent_level(self, client: TestClient):
        """Returns empty list for level with no sections."""
        response = client.get("/api/v1/sections?level=5")

        assert response.status_code == 200
        data = response.json()

        assert data["level"] == 5
        assert data["sections"] == []
        assert data["count"] == 0

    def test_get_sections_requires_level_parameter(self, client: TestClient):
        """Level parameter is required."""
        response = client.get("/api/v1/sections")

        assert response.status_code == 422  # Validation error


class TestEmptyIndex:
    """Tests for API behavior with empty index."""

    @pytest.fixture
    def empty_client(self) -> TestClient:
        """Create a test client with empty index."""
        index = StructureIndex()
        index.build_from_documents([])
        app = create_app(index)
        return TestClient(app)

    def test_empty_structure_returns_200(self, empty_client: TestClient):
        """Empty index returns 200 with empty structure."""
        response = empty_client.get("/api/v1/structure")

        assert response.status_code == 200
        data = response.json()

        assert data["sections"] == []
        assert data["total_sections"] == 0

    def test_empty_sections_returns_200(self, empty_client: TestClient):
        """Empty index returns 200 with empty sections list."""
        response = empty_client.get("/api/v1/sections?level=1")

        assert response.status_code == 200
        data = response.json()

        assert data["sections"] == []
        assert data["count"] == 0
