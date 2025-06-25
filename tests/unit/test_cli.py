#!/usr/bin/env python3
"""
Tests for the CLI module
"""

import json
from pathlib import Path

from click.testing import CliRunner

from autodoc.cli import cli


class TestCLIIntegration:
    """Test CLI command integration"""

    def test_cli_check_command(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        # Clear any existing API key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        runner = CliRunner()

        # Test without API key
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        assert "OpenAI API key not found" in result.output

        # Test with API key
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        assert "OpenAI API key configured" in result.output

    def test_analyze_command(self, sample_project_dir):
        runner = CliRunner()
        # Use catch_exceptions=False to see actual errors
        result = runner.invoke(cli, ["analyze", str(sample_project_dir)], catch_exceptions=False)

        # The command should complete successfully
        assert result.exit_code == 0
        assert "Found" in result.output or "Analysis Summary" in result.output

    def test_generate_summary_command(self, tmp_path):
        # Create a cache file with test data
        cache_data = {
            "entities": [
                {
                    "type": "function",
                    "name": "test_func",
                    "file_path": "test.py",  # Use relative path
                    "line_number": 1,
                    "docstring": "Test function",
                    "code": "def test_func():",
                    "embedding": None,
                }
            ]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create cache file in the isolated filesystem
            cache_file = Path("autodoc_cache.json")
            cache_file.write_text(json.dumps(cache_data))

            result = runner.invoke(cli, ["generate-summary", "--format", "json"])

            assert result.exit_code == 0
            assert "total_functions" in result.output or "functions" in result.output

    def test_search_command_no_cache(self, tmp_path):
        """Test search command when no cache exists"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["search", "test query"])

            assert result.exit_code == 0
            assert "No analyzed code found" in result.output

    def test_help_command(self):
        """Test that help command works"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Autodoc - AI-powered code intelligence" in result.output

    def test_graph_commands_without_dependencies(self, monkeypatch):
        """Test that graph commands handle missing dependencies gracefully"""
        # Mock GRAPH_AVAILABLE to False
        import autodoc.cli

        monkeypatch.setattr(autodoc.cli, "GRAPH_AVAILABLE", False)

        runner = CliRunner()

        # Test build-graph command
        result = runner.invoke(cli, ["build-graph"])
        assert result.exit_code == 0
        assert "Graph functionality not available" in result.output

        # Test visualize-graph command
        result = runner.invoke(cli, ["visualize-graph"])
        assert result.exit_code == 0
        assert "Graph functionality not available" in result.output

        # Test query-graph command
        result = runner.invoke(cli, ["query-graph", "--all"])
        assert result.exit_code == 0
        assert "Graph functionality not available" in result.output


class TestCLICommands:
    """Test individual CLI command functionality"""

    def test_analyze_command_with_save(self, sample_project_dir, tmp_path):
        """Test analyze command with --save flag"""
        runner = CliRunner()

        # Change to temp directory so cache is created there
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["analyze", str(sample_project_dir), "--save"])

            assert result.exit_code == 0
            # Check that cache file was created
            assert Path("autodoc_cache.json").exists()

    def test_generate_summary_formats(self, tmp_path):
        """Test generate-summary with different formats"""
        cache_data = {
            "entities": [
                {
                    "type": "function",
                    "name": "test_func",
                    "file_path": "test.py",
                    "line_number": 1,
                    "docstring": "Test function",
                    "code": "def test_func():",
                    "embedding": None,
                }
            ]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            cache_file = Path("autodoc_cache.json")
            cache_file.write_text(json.dumps(cache_data))

            # Test JSON format
            result = runner.invoke(cli, ["generate-summary", "--format", "json"])
            assert result.exit_code == 0
            assert "total_functions" in result.output or "functions" in result.output

            # Test Markdown format (default)
            result = runner.invoke(cli, ["generate-summary", "--format", "markdown"])
            assert result.exit_code == 0
