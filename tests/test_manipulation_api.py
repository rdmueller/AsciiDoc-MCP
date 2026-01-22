"""Tests for Manipulation API endpoints.

These tests verify the Manipulation API endpoints:
- PUT /api/v1/section/{path}
- POST /api/v1/section/{path}/insert
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dacli.api.app import create_app
from dacli.models import Document, Section, SourceLocation
from dacli.structure_index import StructureIndex


@pytest.fixture
def temp_doc_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test documents."""
    # Create a simple AsciiDoc file
    doc_file = tmp_path / "test.adoc"
    doc_file.write_text(
        """= Test Document

== Introduction

This is the introduction section.
It has multiple lines.

=== Goals

These are the goals.

== Constraints

This is the constraints section.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def sample_index(temp_doc_dir: Path) -> StructureIndex:
    """Create a sample index with test data."""
    doc_file = temp_doc_dir / "test.adoc"
    index = StructureIndex()
    doc = Document(
        file_path=doc_file,
        title="Test Document",
        sections=[
            Section(
                title="Introduction",
                level=1,
                path="/introduction",
                source_location=SourceLocation(file=doc_file, line=3),
                children=[
                    Section(
                        title="Goals",
                        level=2,
                        path="/introduction/goals",
                        source_location=SourceLocation(file=doc_file, line=8),
                    ),
                ],
            ),
            Section(
                title="Constraints",
                level=1,
                path="/constraints",
                source_location=SourceLocation(file=doc_file, line=12),
            ),
        ],
        elements=[],
    )
    index.build_from_documents([doc])
    return index


@pytest.fixture
def client(sample_index: StructureIndex) -> TestClient:
    """Create a test client with the sample index."""
    app = create_app(sample_index)
    return TestClient(app)


# =============================================================================
# PUT /section/{path} Tests (UC-03)
# =============================================================================


class TestUpdateSection:
    """Tests for PUT /api/v1/section/{path} endpoint."""

    def test_update_section_returns_200(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: PUT /section/{path} returns 200 for successful update."""
        response = client.put(
            "/api/v1/section/introduction",
            json={"content": "== Introduction\n\nUpdated content.\n"},
        )
        assert response.status_code == 200

    def test_update_section_success_response(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: Successful update returns expected fields."""
        response = client.put(
            "/api/v1/section/introduction",
            json={"content": "== Introduction\n\nUpdated content.\n"},
        )
        data = response.json()

        assert data["success"] is True
        assert data["path"] == "/introduction"
        assert "location" in data
        assert "file" in data["location"]

    def test_update_section_content_written(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: Content is actually written to file."""
        new_content = "== Introduction\n\nCompletely new content here.\n"
        client.put(
            "/api/v1/section/introduction",
            json={"content": new_content},
        )

        # Read the file and verify content was updated
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "Completely new content here" in file_content

    def test_update_section_not_found(self, client: TestClient):
        """UC-03: Returns 404 for non-existent section."""
        response = client.put(
            "/api/v1/section/nonexistent",
            json={"content": "Some content"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PATH_NOT_FOUND"

    def test_update_section_preserve_title_default(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: preserve_title defaults to true."""
        # Update with content that doesn't include title
        response = client.put(
            "/api/v1/section/introduction",
            json={"content": "Just the body content.\n"},
        )

        assert response.status_code == 200
        # The original title should be preserved
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== Introduction" in file_content

    def test_update_section_preserve_title_false(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: preserve_title=false replaces everything."""
        response = client.put(
            "/api/v1/section/introduction",
            json={
                "content": "== New Title\n\nNew content.\n",
                "preserve_title": False,
            },
        )

        assert response.status_code == 200
        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "== New Title" in file_content

    def test_update_section_atomic_on_error(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-03: Original file unchanged if write fails."""
        doc_file = temp_doc_dir / "test.adoc"
        original_content = doc_file.read_text(encoding="utf-8")

        # Mock file handler instance to raise an error
        with patch(
            "dacli.api.manipulation._file_handler.update_section"
        ) as mock_update:
            from dacli.file_handler import FileWriteError

            mock_update.side_effect = FileWriteError("Simulated write failure")

            response = client.put(
                "/api/v1/section/introduction",
                json={"content": "Should fail"},
            )

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"]["code"] == "WRITE_FAILED"

        # Original should be unchanged (mock prevented actual write)
        # In real scenario, FileSystemHandler's atomic write ensures this
        current_content = doc_file.read_text(encoding="utf-8")
        assert current_content == original_content

    def test_update_section_requires_content(self, client: TestClient):
        """UC-03: content field is required."""
        response = client.put("/api/v1/section/introduction", json={})

        assert response.status_code == 422  # Validation error


# =============================================================================
# POST /section/{path}/insert Tests (UC-09)
# =============================================================================


class TestInsertContent:
    """Tests for POST /api/v1/section/{path}/insert endpoint."""

    def test_insert_after_returns_200(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-09: POST /section/{path}/insert returns 200."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "after",
                "content": "== New Section\n\nNew content.\n",
            },
        )
        assert response.status_code == 200

    def test_insert_after_success_response(
        self, client: TestClient, temp_doc_dir: Path
    ):
        """UC-09: Successful insert returns expected fields."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "after",
                "content": "== Summary\n\nThis is a summary.\n",
            },
        )
        data = response.json()

        assert data["success"] is True
        assert "inserted_at" in data
        assert "file" in data["inserted_at"]
        assert "line" in data["inserted_at"]

    def test_insert_before(self, client: TestClient, temp_doc_dir: Path):
        """UC-09: Insert content before a section."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "before",
                "content": "== Preface\n\nThis is a preface.\n",
            },
        )

        assert response.status_code == 200

        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        # Preface should appear before Introduction
        preface_pos = file_content.find("== Preface")
        intro_pos = file_content.find("== Introduction")
        assert preface_pos < intro_pos

    def test_insert_after(self, client: TestClient, temp_doc_dir: Path):
        """UC-09: Insert content after a section."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "after",
                "content": "\n== Summary\n\nThis is a summary.\n",
            },
        )

        assert response.status_code == 200

        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        # Summary should appear in the file
        assert "== Summary" in file_content

    def test_insert_append(self, client: TestClient, temp_doc_dir: Path):
        """UC-09: Append content to end of section."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "append",
                "content": "\nAdditional paragraph at end.\n",
            },
        )

        assert response.status_code == 200

        doc_file = temp_doc_dir / "test.adoc"
        file_content = doc_file.read_text(encoding="utf-8")
        assert "Additional paragraph at end" in file_content

    def test_insert_invalid_position(self, client: TestClient):
        """UC-09: Invalid position returns 422 (validation error)."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={
                "position": "invalid",
                "content": "Some content",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_insert_section_not_found(self, client: TestClient):
        """UC-09: Returns 404 for non-existent section."""
        response = client.post(
            "/api/v1/section/nonexistent/insert",
            json={
                "position": "after",
                "content": "Some content",
            },
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PATH_NOT_FOUND"

    def test_insert_requires_position(self, client: TestClient):
        """UC-09: position field is required."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={"content": "Some content"},
        )

        assert response.status_code == 422

    def test_insert_requires_content(self, client: TestClient):
        """UC-09: content field is required."""
        response = client.post(
            "/api/v1/section/introduction/insert",
            json={"position": "after"},
        )

        assert response.status_code == 422


# =============================================================================
# Empty Index Tests
# =============================================================================


class TestEmptyIndex:
    """Tests for API behavior with empty index."""

    @pytest.fixture
    def empty_client(self, tmp_path: Path) -> TestClient:
        """Create a test client with empty index."""
        index = StructureIndex()
        index.build_from_documents([])
        app = create_app(index)
        return TestClient(app)

    def test_update_empty_index_returns_404(self, empty_client: TestClient):
        """Empty index update returns 404."""
        response = empty_client.put(
            "/api/v1/section/any",
            json={"content": "content"},
        )

        assert response.status_code == 404

    def test_insert_empty_index_returns_404(self, empty_client: TestClient):
        """Empty index insert returns 404."""
        response = empty_client.post(
            "/api/v1/section/any/insert",
            json={"position": "after", "content": "content"},
        )

        assert response.status_code == 404
