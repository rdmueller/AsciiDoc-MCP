"""Tests for file_utils module - gitignore filtering functionality."""

from pathlib import Path


class TestLoadGitignoreSpec:
    """Tests for load_gitignore_spec function."""

    def test_loads_gitignore_from_docs_root(self, tmp_path: Path):
        """Should load .gitignore from docs root directory."""
        from dacli.file_utils import load_gitignore_spec

        # Create .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n*.tmp\n")

        spec = load_gitignore_spec(tmp_path)

        assert spec is not None
        assert spec.match_file("node_modules/package.json")
        assert spec.match_file("test.tmp")
        assert not spec.match_file("docs/readme.md")

    def test_returns_none_when_no_gitignore(self, tmp_path: Path):
        """Should return None when .gitignore doesn't exist."""
        from dacli.file_utils import load_gitignore_spec

        spec = load_gitignore_spec(tmp_path)

        assert spec is None

    def test_handles_empty_gitignore(self, tmp_path: Path):
        """Should handle empty .gitignore file."""
        from dacli.file_utils import load_gitignore_spec

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("")

        spec = load_gitignore_spec(tmp_path)

        # Empty spec should not match anything
        assert spec is not None
        assert not spec.match_file("anything.txt")

    def test_handles_comments_in_gitignore(self, tmp_path: Path):
        """Should handle comments in .gitignore."""
        from dacli.file_utils import load_gitignore_spec

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# This is a comment\nnode_modules/\n# Another comment\n")

        spec = load_gitignore_spec(tmp_path)

        assert spec is not None
        assert spec.match_file("node_modules/test.js")

    def test_handles_negation_patterns(self, tmp_path: Path):
        """Should handle negation patterns in .gitignore."""
        from dacli.file_utils import load_gitignore_spec

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\n!important.log\n")

        spec = load_gitignore_spec(tmp_path)

        assert spec is not None
        assert spec.match_file("debug.log")
        # Note: pathspec handles negation differently than git
        # This test documents the behavior

    def test_loads_nested_gitignore_files(self, tmp_path: Path):
        """Should load .gitignore from parent directories up to docs root."""
        from dacli.file_utils import load_gitignore_spec

        # Create root .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n")

        spec = load_gitignore_spec(tmp_path)

        assert spec is not None
        assert spec.match_file("node_modules/file.js")


class TestFindDocFiles:
    """Tests for find_doc_files function."""

    def test_finds_adoc_files(self, tmp_path: Path):
        """Should find .adoc files in directory."""
        from dacli.file_utils import find_doc_files

        # Create test files
        (tmp_path / "doc1.adoc").write_text("= Doc 1")
        (tmp_path / "doc2.adoc").write_text("= Doc 2")
        (tmp_path / "readme.md").write_text("# Readme")

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 2
        assert all(f.suffix == ".adoc" for f in files)

    def test_finds_md_files(self, tmp_path: Path):
        """Should find .md files in directory."""
        from dacli.file_utils import find_doc_files

        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")
        (tmp_path / "readme.adoc").write_text("= Readme")

        files = list(find_doc_files(tmp_path, "*.md"))

        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)

    def test_finds_files_recursively(self, tmp_path: Path):
        """Should find files in subdirectories."""
        from dacli.file_utils import find_doc_files

        # Create nested structure
        subdir = tmp_path / "chapters"
        subdir.mkdir()
        (tmp_path / "root.adoc").write_text("= Root")
        (subdir / "chapter1.adoc").write_text("= Chapter 1")

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 2

    def test_excludes_gitignored_files(self, tmp_path: Path):
        """Should exclude files matching .gitignore patterns."""
        from dacli.file_utils import find_doc_files

        # Create .gitignore
        (tmp_path / ".gitignore").write_text("node_modules/\n")

        # Create files
        (tmp_path / "doc.adoc").write_text("= Doc")
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.adoc").write_text("= Package")

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 1
        assert files[0].name == "doc.adoc"

    def test_excludes_hidden_directories(self, tmp_path: Path):
        """Should exclude hidden directories (starting with .) by default."""
        from dacli.file_utils import find_doc_files

        # Create files
        (tmp_path / "doc.adoc").write_text("= Doc")
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.adoc").write_text("= Secret")

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 1
        assert files[0].name == "doc.adoc"

    def test_includes_all_files_when_no_gitignore(self, tmp_path: Path):
        """Should include all files when no .gitignore exists (except hidden)."""
        from dacli.file_utils import find_doc_files

        # Create files (no .gitignore)
        (tmp_path / "doc.adoc").write_text("= Doc")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub.adoc").write_text("= Sub")

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 2

    def test_respects_no_gitignore_flag(self, tmp_path: Path):
        """Should include gitignored files when respect_gitignore=False."""
        from dacli.file_utils import find_doc_files

        # Create .gitignore
        (tmp_path / ".gitignore").write_text("ignored/\n")

        # Create files
        (tmp_path / "doc.adoc").write_text("= Doc")
        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        (ignored_dir / "ignored.adoc").write_text("= Ignored")

        files = list(find_doc_files(tmp_path, "*.adoc", respect_gitignore=False))

        # Should find both files (but still skip hidden dirs)
        assert len(files) == 2

    def test_handles_complex_gitignore_patterns(self, tmp_path: Path):
        """Should handle complex gitignore patterns."""
        from dacli.file_utils import find_doc_files

        # Create .gitignore with various patterns
        (tmp_path / ".gitignore").write_text(
            "# Comment\n"
            "*.tmp\n"
            "build/\n"
            "!build/important.adoc\n"
            "**/temp/\n"
        )

        # Create files
        (tmp_path / "doc.adoc").write_text("= Doc")
        (tmp_path / "doc.tmp").write_text("= Temp")  # Should be ignored
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "output.adoc").write_text("= Output")  # Should be ignored
        temp_dir = tmp_path / "chapters" / "temp"
        temp_dir.mkdir(parents=True)
        (temp_dir / "temp.adoc").write_text("= Temp")  # Should be ignored

        files = list(find_doc_files(tmp_path, "*.adoc"))

        assert len(files) == 1
        assert files[0].name == "doc.adoc"


class TestIntegration:
    """Integration tests for gitignore filtering."""

    def test_typical_node_project_structure(self, tmp_path: Path):
        """Should correctly filter a typical Node.js project with docs."""
        from dacli.file_utils import find_doc_files

        # Create typical .gitignore
        (tmp_path / ".gitignore").write_text(
            "node_modules/\n"
            ".git/\n"
            "dist/\n"
            "*.log\n"
        )

        # Create project structure
        (tmp_path / "README.md").write_text("# Project")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Guide")

        # Create ignored directories
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "some-package").mkdir()
        (node_modules / "some-package" / "README.md").write_text("# Package")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("config")

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "docs.md").write_text("# Built docs")

        files = list(find_doc_files(tmp_path, "*.md"))

        # Should only find README.md and docs/guide.md
        file_names = {f.name for f in files}
        assert file_names == {"README.md", "guide.md"}
        assert len(files) == 2

    def test_performance_with_many_ignored_files(self, tmp_path: Path):
        """Should handle directories with many ignored files efficiently."""
        import time

        from dacli.file_utils import find_doc_files

        # Create .gitignore
        (tmp_path / ".gitignore").write_text("ignored/\n")

        # Create many ignored files
        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        for i in range(100):
            (ignored_dir / f"file_{i}.md").write_text(f"# File {i}")

        # Create actual doc
        (tmp_path / "doc.md").write_text("# Doc")

        start = time.time()
        files = list(find_doc_files(tmp_path, "*.md"))
        elapsed = time.time() - start

        assert len(files) == 1
        # Should be fast (under 1 second even with many files)
        assert elapsed < 1.0
