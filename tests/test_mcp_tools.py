"""Tests for MCP Tools.

These tests verify the FastMCP tools work correctly for document navigation,
content access, and manipulation.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from fastmcp.client import Client

from mcp_server.mcp_app import create_mcp_server


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


@pytest_asyncio.fixture
async def mcp_client(temp_doc_dir: Path):
    """Create an MCP client for testing."""
    mcp = create_mcp_server(docs_root=temp_doc_dir)
    async with Client(transport=mcp) as client:
        yield client


# =============================================================================
# Tool Discovery Tests
# =============================================================================


class TestToolDiscovery:
    """Tests for MCP tool registration and discovery."""

    async def test_tools_are_registered(self, mcp_client: Client):
        """All expected tools should be registered."""
        tools = await mcp_client.list_tools()
        tool_names = {tool.name for tool in tools}

        expected_tools = {
            "get_structure",
            "get_section",
            "get_sections_at_level",
            "search",
            "update_section",
            "insert_content",
            "get_elements",
        }
        assert expected_tools.issubset(tool_names)

    async def test_tools_have_descriptions(self, mcp_client: Client):
        """All tools should have descriptions for LLM context."""
        tools = await mcp_client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"


# =============================================================================
# Navigation Tools Tests
# =============================================================================


class TestGetStructure:
    """Tests for get_structure tool."""

    async def test_get_structure_returns_sections(self, mcp_client: Client):
        """get_structure returns document sections."""
        result = await mcp_client.call_tool("get_structure", arguments={})

        assert "sections" in result.data
        assert "total_sections" in result.data
        assert result.data["total_sections"] > 0

    async def test_get_structure_with_max_depth(self, mcp_client: Client):
        """get_structure respects max_depth parameter."""
        result = await mcp_client.call_tool(
            "get_structure", arguments={"max_depth": 1}
        )

        assert "sections" in result.data
        # At depth 1, children should be empty or limited
        for section in result.data["sections"]:
            # Children at depth 1 should exist but their children should be empty
            if section.get("children"):
                for child in section["children"]:
                    assert child.get("children", []) == []


class TestGetSection:
    """Tests for get_section tool."""

    async def test_get_section_returns_content(self, mcp_client: Client):
        """get_section returns section with content."""
        # Note: Paths use dot notation with document title prefix
        # e.g., "test-document.introduction" not "/introduction"
        result = await mcp_client.call_tool(
            "get_section", arguments={"path": "test-document.introduction"}
        )

        assert result.data is not None
        assert "title" in result.data
        assert "content" in result.data
        assert "Introduction" in result.data["title"]

    async def test_get_section_not_found(self, mcp_client: Client):
        """get_section returns error for non-existent path."""
        result = await mcp_client.call_tool(
            "get_section", arguments={"path": "nonexistent"}
        )

        # Implementation returns dict with "error" key for not found
        assert "error" in result.data


class TestGetSectionsAtLevel:
    """Tests for get_sections_at_level tool."""

    async def test_get_level_1_sections(self, mcp_client: Client):
        """get_sections_at_level returns sections at level 1 (chapters)."""
        result = await mcp_client.call_tool(
            "get_sections_at_level", arguments={"level": 1}
        )

        assert "level" in result.data
        assert result.data["level"] == 1
        assert "sections" in result.data
        assert "count" in result.data

        # Test document has 2 level-1 sections: Introduction, Constraints
        sections = result.data["sections"]
        assert len(sections) == 2
        titles = [s["title"] for s in sections]
        assert "Introduction" in titles
        assert "Constraints" in titles

    async def test_get_level_2_sections(self, mcp_client: Client):
        """get_sections_at_level returns sections at level 2 (sub-sections)."""
        result = await mcp_client.call_tool(
            "get_sections_at_level", arguments={"level": 2}
        )

        assert result.data["level"] == 2
        sections = result.data["sections"]
        # Test document has 1 level-2 section: Goals
        assert len(sections) == 1
        assert sections[0]["title"] == "Goals"

    async def test_get_sections_empty_level(self, mcp_client: Client):
        """get_sections_at_level returns empty list for levels with no sections."""
        result = await mcp_client.call_tool(
            "get_sections_at_level", arguments={"level": 5}
        )

        assert result.data["level"] == 5
        assert result.data["sections"] == []
        assert result.data["count"] == 0

    async def test_get_sections_has_path_and_title(self, mcp_client: Client):
        """get_sections_at_level returns sections with path and title."""
        result = await mcp_client.call_tool(
            "get_sections_at_level", arguments={"level": 1}
        )

        for section in result.data["sections"]:
            assert "path" in section
            assert "title" in section


# =============================================================================
# Content Access Tools Tests
# =============================================================================


class TestSearch:
    """Tests for search tool."""

    async def test_search_finds_content(self, mcp_client: Client):
        """search finds matching content."""
        result = await mcp_client.call_tool(
            "search", arguments={"query": "introduction"}
        )

        assert "results" in result.data
        assert len(result.data["results"]) > 0

    async def test_search_with_max_results(self, mcp_client: Client):
        """search respects max_results parameter."""
        result = await mcp_client.call_tool(
            "search", arguments={"query": "section", "max_results": 1}
        )

        assert len(result.data["results"]) <= 1


class TestGetElements:
    """Tests for get_elements tool."""

    async def test_get_elements_returns_list(self, mcp_client: Client):
        """get_elements returns element list."""
        result = await mcp_client.call_tool("get_elements", arguments={})

        assert "elements" in result.data
        assert isinstance(result.data["elements"], list)


# =============================================================================
# Manipulation Tools Tests
# =============================================================================


class TestUpdateSection:
    """Tests for update_section tool."""

    async def test_update_section_success(self, mcp_client: Client, temp_doc_dir: Path):
        """update_section modifies section content."""
        result = await mcp_client.call_tool(
            "update_section",
            arguments={
                "path": "test-document.introduction",
                "content": "== Introduction\n\nUpdated content.\n",
            },
        )

        assert result.data["success"] is True

        # Verify file was updated
        doc_file = temp_doc_dir / "test.adoc"
        content = doc_file.read_text(encoding="utf-8")
        assert "Updated content" in content

    async def test_update_section_preserve_title(
        self, mcp_client: Client, temp_doc_dir: Path
    ):
        """update_section preserves title by default."""
        result = await mcp_client.call_tool(
            "update_section",
            arguments={
                "path": "test-document.introduction",
                "content": "New body content only.\n",
                "preserve_title": True,
            },
        )

        assert result.data["success"] is True

        doc_file = temp_doc_dir / "test.adoc"
        content = doc_file.read_text(encoding="utf-8")
        assert "== Introduction" in content
        assert "New body content only" in content


class TestInsertContent:
    """Tests for insert_content tool."""

    async def test_insert_after_section(self, mcp_client: Client, temp_doc_dir: Path):
        """insert_content adds content after section."""
        doc_file = temp_doc_dir / "test.adoc"

        result = await mcp_client.call_tool(
            "insert_content",
            arguments={
                "path": "test-document.introduction",
                "position": "after",
                "content": "== New Section\n\nNew content.\n",
            },
        )

        assert result.data["success"] is True
        assert "inserted_at" in result.data
        assert "line" in result.data["inserted_at"]

        content = doc_file.read_text(encoding="utf-8")
        assert "== New Section" in content
        # Verify original content is preserved
        assert "== Introduction" in content
        assert "== Constraints" in content
        # New section should be after Introduction's content
        intro_pos = content.find("== Introduction")
        new_section_pos = content.find("== New Section")
        assert intro_pos < new_section_pos

    async def test_insert_before_section(self, mcp_client: Client, temp_doc_dir: Path):
        """insert_content adds content before section."""
        doc_file = temp_doc_dir / "test.adoc"

        result = await mcp_client.call_tool(
            "insert_content",
            arguments={
                "path": "test-document.introduction",
                "position": "before",
                "content": "== Preface\n\nPreface content.\n",
            },
        )

        assert result.data["success"] is True
        assert "inserted_at" in result.data

        content = doc_file.read_text(encoding="utf-8")
        # Verify all sections exist
        assert "== Preface" in content
        assert "== Introduction" in content
        assert "== Constraints" in content
        # Preface should be before Introduction
        preface_pos = content.find("== Preface")
        intro_pos = content.find("== Introduction")
        assert preface_pos < intro_pos

    async def test_insert_invalid_position(self, mcp_client: Client):
        """insert_content returns error for invalid position."""
        result = await mcp_client.call_tool(
            "insert_content",
            arguments={
                "path": "test-document.introduction",
                "position": "invalid",
                "content": "Some content",
            },
        )

        assert result.data["success"] is False
        assert "error" in result.data
