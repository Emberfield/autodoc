#!/usr/bin/env python3
"""
Tests for the main autodoc module
"""

from unittest.mock import Mock, patch

import pytest

from autodoc.analyzer import CodeEntity
from autodoc.autodoc import SimpleAutodoc


class TestSimpleAutodoc:
    """Test main Autodoc functionality"""

    @pytest.mark.asyncio
    async def test_analyze_directory(self, sample_project_dir, monkeypatch):
        # Clear API key to ensure no embedder
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        autodoc = SimpleAutodoc()
        summary = await autodoc.analyze_directory(sample_project_dir)

        assert summary["files_analyzed"] >= 2
        assert summary["total_entities"] > 0
        assert summary["functions"] > 0
        assert summary["classes"] > 0
        assert summary["has_embeddings"] is False

    @pytest.mark.asyncio
    async def test_analyze_with_embeddings(self, sample_project_dir, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("autodoc.embedder.OpenAIEmbedder.embed_batch") as mock_embed:
            mock_embed.return_value = [[0.1, 0.2] for _ in range(20)]  # More embeddings

            autodoc = SimpleAutodoc()
            summary = await autodoc.analyze_directory(sample_project_dir)

            assert summary["has_embeddings"] is True
            assert all(e.embedding is not None for e in autodoc.entities)

    def test_save_and_load(self, tmp_path):
        autodoc = SimpleAutodoc()

        # Create some test entities
        autodoc.entities = [
            CodeEntity(
                type="function",
                name="test_func",
                file_path="/test.py",
                line_number=1,
                docstring="Test",
                code="def test_func(): pass",
                embedding=[0.1, 0.2],
            )
        ]

        # Save
        cache_file = tmp_path / "test_cache.json"
        autodoc.save(str(cache_file))

        assert cache_file.exists()

        # Load into new instance
        new_autodoc = SimpleAutodoc()
        new_autodoc.load(str(cache_file))

        assert len(new_autodoc.entities) == 1
        assert new_autodoc.entities[0].name == "test_func"
        assert new_autodoc.entities[0].embedding == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_search_with_embeddings(self, sample_code_entities):
        autodoc = SimpleAutodoc()
        autodoc.entities = sample_code_entities

        with patch("autodoc.embedder.OpenAIEmbedder.embed") as mock_embed:
            mock_embed.return_value = [0.8, 0.2]  # Similar to process_data

            autodoc.embedder = Mock()
            autodoc.embedder.embed = mock_embed

            results = await autodoc.search("data processing", limit=2)

            assert len(results) == 2
            # First result should be process_data due to similarity
            assert results[0]["entity"]["name"] == "process_data"
            assert results[0]["similarity"] > results[1]["similarity"]

    @pytest.mark.asyncio
    async def test_search_without_embeddings(self, sample_code_entities):
        autodoc = SimpleAutodoc()
        # Remove embeddings to test text search
        for entity in sample_code_entities:
            entity.embedding = None
        autodoc.entities = sample_code_entities

        results = await autodoc.search("data", limit=2)

        assert len(results) >= 1
        assert results[0]["entity"]["name"] == "process_data"

    def test_generate_summary(self, sample_project_dir):
        autodoc = SimpleAutodoc()
        # Manually add some entities for testing
        autodoc.entities = [
            CodeEntity(
                type="function",
                name="main",
                file_path=str(sample_project_dir / "main.py"),
                line_number=1,
                docstring="Main entry point",
                code="def main():",
            ),
            CodeEntity(
                type="class",
                name="Config",
                file_path=str(sample_project_dir / "config.py"),
                line_number=10,
                docstring="Configuration class",
                code="class Config:",
            ),
            CodeEntity(
                type="function",
                name="test_something",
                file_path=str(sample_project_dir / "tests" / "test_main.py"),
                line_number=5,
                docstring="Test something",
                code="def test_something():",
            ),
        ]

        summary = autodoc.generate_summary()

        assert "overview" in summary
        assert "statistics" in summary
        assert "modules" in summary
        assert "feature_map" in summary
        assert "entry_points" in summary

        # Check entry points detection
        assert any(ep["name"] == "main" for ep in summary["entry_points"])

        # Check feature map
        assert "testing" in summary["feature_map"]
        assert "configuration" in summary["feature_map"]

    def test_format_summary_markdown(self):
        autodoc = SimpleAutodoc()

        # Create a minimal summary
        summary = {
            "overview": {
                "total_files": 3,
                "total_functions": 10,
                "total_classes": 2,
                "has_tests": True,
                "main_language": "Python",
                "analysis_date": "2024-01-01",
                "tool_version": "autodoc 0.1.0",
                "total_lines_analyzed": 500,
            },
            "statistics": {
                "total_entities": 12,
                "public_functions": 8,
                "private_functions": 2,
                "test_functions": 2,
                "documentation_coverage": 0.75,
                "avg_functions_per_file": 3.3,
                "avg_classes_per_file": 0.7,
            },
            "modules": {
                "main": {
                    "file_path": "/project/main.py",
                    "relative_path": "main.py",
                    "purpose": "Main module",
                    "functions": [],
                    "classes": [],
                    "complexity_score": 5.0,
                    "exports": ["main_function"],
                }
            },
        }

        markdown = autodoc.format_summary_markdown(summary)

        assert "# Comprehensive Codebase Documentation" in markdown
        assert "## Executive Summary" in markdown
        assert "10 functions and 2 classes" in markdown
        assert "75.0%" in markdown  # Documentation coverage

    def test_initialization_without_api_key(self, monkeypatch):
        """Test that autodoc initializes correctly without OpenAI API key"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        autodoc = SimpleAutodoc()
        assert autodoc.embedder is None
        assert autodoc.analyzer is not None

    def test_initialization_with_api_key(self, monkeypatch):
        """Test that autodoc initializes correctly with OpenAI API key"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        autodoc = SimpleAutodoc()
        assert autodoc.embedder is not None
        assert autodoc.analyzer is not None
