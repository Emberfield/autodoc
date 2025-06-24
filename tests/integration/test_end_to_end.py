#!/usr/bin/env python3
"""
End-to-end integration tests for Autodoc
"""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from autodoc.autodoc import SimpleAutodoc
from autodoc.cli import cli


class TestEndToEndWorkflow:
    """Test complete workflows from analysis to search"""

    @pytest.mark.asyncio
    async def test_full_python_api_workflow(self, sample_project_dir, monkeypatch):
        """Test complete workflow using Python API"""
        # Clear API key to ensure reproducible test
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Initialize autodoc
        autodoc = SimpleAutodoc()

        # Analyze directory
        summary = await autodoc.analyze_directory(sample_project_dir)

        # Verify analysis results
        assert summary["files_analyzed"] >= 2
        assert summary["total_entities"] > 0
        assert summary["functions"] > 0
        assert summary["classes"] > 0

        # Perform search
        results = await autodoc.search("class", limit=5)
        assert len(results) > 0

        # Generate summary
        detailed_summary = autodoc.generate_summary()
        assert "overview" in detailed_summary
        assert "modules" in detailed_summary

        # Test save/load cycle
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_file = Path(f.name)

        try:
            autodoc.save(str(cache_file))
            assert cache_file.exists()

            # Load into new instance
            new_autodoc = SimpleAutodoc()
            new_autodoc.load(str(cache_file))

            assert len(new_autodoc.entities) == len(autodoc.entities)

            # Search should work with loaded data
            new_results = await new_autodoc.search("function", limit=3)
            assert len(new_results) > 0

        finally:
            cache_file.unlink()

    def test_full_cli_workflow(self, sample_project_dir):
        """Test complete workflow using CLI"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Step 1: Analyze and save
            result = runner.invoke(cli, ["analyze", str(sample_project_dir), "--save"])
            assert result.exit_code == 0
            assert Path("autodoc_cache.json").exists()

            # Step 2: Search
            result = runner.invoke(cli, ["search", "function"])
            assert result.exit_code == 0
            # Should find results
            assert "function" in result.output.lower() or "results" in result.output.lower()

            # Step 3: Generate summary
            result = runner.invoke(cli, ["generate-summary", "--format", "json"])
            assert result.exit_code == 0

            # Step 4: Generate markdown summary
            result = runner.invoke(
                cli, ["generate-summary", "--format", "markdown", "--output", "summary.md"]
            )
            assert result.exit_code == 0
            assert Path("summary.md").exists()

            # Verify markdown content
            markdown_content = Path("summary.md").read_text()
            assert "# Comprehensive Codebase Documentation" in markdown_content

    @pytest.mark.asyncio
    async def test_large_codebase_performance(self, tmp_path, monkeypatch):
        """Test performance with a larger simulated codebase"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create multiple Python files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        for i in range(10):
            module_content = f'''
"""Module {i} for testing"""

class Module{i}Class:
    """Class for module {i}"""
    
    def __init__(self):
        self.value = {i}
    
    def process_{i}(self, data):
        """Process data for module {i}"""
        return data * {i}
    
    def get_value_{i}(self):
        """Get value for module {i}"""
        return self.value

def utility_function_{i}(x, y):
    """Utility function for module {i}"""
    return x + y + {i}

async def async_function_{i}():
    """Async function for module {i}"""
    return await some_async_operation()
'''
            (src_dir / f"module_{i}.py").write_text(module_content)

        # Analyze the codebase
        autodoc = SimpleAutodoc()
        summary = await autodoc.analyze_directory(src_dir)

        # Verify we found all the entities
        assert summary["files_analyzed"] == 10
        assert summary["total_entities"] >= 40  # At least 4 entities per file
        assert summary["functions"] >= 30  # 3 functions per file
        assert summary["classes"] >= 10  # 1 class per file

        # Test search performance
        results = await autodoc.search("process", limit=10)
        assert len(results) == 10  # Should find all process functions

        # Test that all results are relevant
        for result in results:
            assert "process" in result["entity"]["name"].lower()

    def test_error_handling_workflow(self, tmp_path):
        """Test error handling in various scenarios"""
        runner = CliRunner()

        # Test analyze with non-existent directory
        result = runner.invoke(cli, ["analyze", "/nonexistent/directory"])
        assert result.exit_code != 0

        # Test search without cache
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["search", "test"])
            assert result.exit_code == 0
            assert "No analyzed code found" in result.output

        # Test generate-summary without cache
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["generate-summary"])
            assert result.exit_code == 0
            assert "No analyzed code found" in result.output

    @pytest.mark.asyncio
    async def test_mixed_file_types(self, tmp_path, monkeypatch):
        """Test analysis with mixed file types"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create directory with Python and non-Python files
        (tmp_path / "valid.py").write_text(
            '''
def valid_function():
    """A valid function"""
    pass

class ValidClass:
    """A valid class"""
    pass
'''
        )

        (tmp_path / "invalid.txt").write_text("This is not Python code")
        (tmp_path / "empty.py").write_text("")
        (tmp_path / "syntax_error.py").write_text("def broken_func(")

        autodoc = SimpleAutodoc()
        summary = await autodoc.analyze_directory(tmp_path)

        # Should only analyze valid Python files successfully
        assert summary["files_analyzed"] >= 1  # At least the valid.py file
        assert summary["total_entities"] >= 2  # Function and class from valid.py

        # Should handle errors gracefully
        entities = autodoc.entities
        valid_entities = [e for e in entities if "valid" in e.name.lower()]
        assert len(valid_entities) >= 2
