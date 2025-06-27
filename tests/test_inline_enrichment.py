#!/usr/bin/env python3
"""
Tests for inline enrichment functionality.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autodoc.analyzer import CodeEntity
from autodoc.config import AutodocConfig
from autodoc.inline_enrichment import (
    ChangeDetector,
    InlineEnricher,
    InlineEnrichmentResult,
    ModuleEnrichmentGenerator,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    content = '''def add_numbers(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''
    file_path = Path(temp_dir) / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_entities(sample_python_file):
    """Create sample entities for the Python file."""
    return [
        CodeEntity(
            type="function",
            name="add_numbers",
            file_path=str(sample_python_file),
            line_number=1,
            docstring="",
            code="def add_numbers(a, b):\n    return a + b",
            embedding=None,
            is_internal=False
        ),
        CodeEntity(
            type="class",
            name="Calculator",
            file_path=str(sample_python_file),
            line_number=4,
            docstring="",
            code="class Calculator:",
            embedding=None,
            is_internal=False
        ),
        CodeEntity(
            type="function",
            name="multiply",
            file_path=str(sample_python_file),
            line_number=5,
            docstring="",
            code="def multiply(self, x, y):\n        return x * y",
            embedding=None,
            is_internal=False
        )
    ]


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return AutodocConfig()


class TestChangeDetector:
    """Test change detection functionality."""
    
    def test_change_detector_init(self, temp_dir):
        """Test change detector initialization."""
        detector = ChangeDetector(f"{temp_dir}/changes.json")
        assert detector.cache == {}
    
    def test_has_changed_new_file(self, sample_python_file, sample_entities):
        """Test that new files are detected as changed."""
        detector = ChangeDetector()
        assert detector.has_changed(sample_python_file, sample_entities)
    
    def test_mark_processed(self, sample_python_file, sample_entities):
        """Test marking file as processed."""
        detector = ChangeDetector()
        detector.mark_processed(sample_python_file, sample_entities)
        
        # Should not be changed after processing
        assert not detector.has_changed(sample_python_file, sample_entities)
    
    def test_get_changed_files(self, sample_python_file, sample_entities):
        """Test getting list of changed files."""
        detector = ChangeDetector()
        changed = detector.get_changed_files(sample_entities)
        
        assert str(sample_python_file) in changed


class TestInlineEnricher:
    """Test inline enrichment functionality."""
    
    def test_inline_enricher_init(self, mock_config):
        """Test inline enricher initialization."""
        enricher = InlineEnricher(mock_config)
        assert enricher.config == mock_config
        assert enricher.backup is True
    
    def test_backup_file(self, sample_python_file, mock_config):
        """Test file backup functionality."""
        enricher = InlineEnricher(mock_config, backup=True)
        original_content = sample_python_file.read_text()
        
        enricher._backup_file(sample_python_file)
        
        backup_file = sample_python_file.with_suffix(".py.autodoc_backup")
        assert backup_file.exists()
        assert backup_file.read_text() == original_content
    
    def test_parse_python_file(self, sample_python_file, mock_config):
        """Test Python file parsing."""
        enricher = InlineEnricher(mock_config)
        tree = enricher._parse_python_file(sample_python_file)
        
        assert tree is not None
    
    def test_should_update_docstring(self, mock_config):
        """Test docstring update logic."""
        enricher = InlineEnricher(mock_config)
        
        # Should update if no existing docstring
        assert enricher._should_update_docstring(None, "New description")
        
        # Should not update substantial existing docstring
        existing = "A comprehensive function that does X.\n\nArgs:\n    param: description"
        assert not enricher._should_update_docstring(existing, "Simple description")
        
        # Should update if enriched is much better
        simple_existing = "Basic function"
        detailed_enriched = "Comprehensive function that handles complex operations with multiple features and examples"
        assert enricher._should_update_docstring(simple_existing, detailed_enriched)
    
    def test_format_docstring(self, sample_entities, mock_config):
        """Test docstring formatting."""
        enricher = InlineEnricher(mock_config)
        entity = sample_entities[0]
        enrichment = {
            "description": "Adds two numbers together",
            "key_features": ["Simple addition", "Returns sum"],
            "usage_examples": ["add_numbers(2, 3)"],
            "complexity_notes": "O(1) time complexity"
        }
        
        docstring = enricher._format_docstring("Adds two numbers", entity, enrichment)
        
        assert "Adds two numbers" in docstring
        assert "Key features:" in docstring
        assert "Simple addition" in docstring
        assert "Examples:" in docstring
        assert "Complexity:" in docstring
    
    @pytest.mark.asyncio
    async def test_enrich_files_inline_mock(self, sample_python_file, sample_entities, mock_config):
        """Test inline enrichment with mocked LLM."""
        enricher = InlineEnricher(mock_config, backup=False)
        
        # Mock the enrichment cache and LLM enricher
        with patch('autodoc.inline_enrichment.EnrichmentCache') as mock_cache_class, \
             patch('autodoc.inline_enrichment.LLMEnricher') as mock_enricher_class:
            
            # Setup mocks
            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache
            mock_cache.get_enrichment.return_value = {
                "description": "Enhanced description for the function",
                "purpose": "To demonstrate inline enrichment",
                "key_features": ["Fast", "Reliable"],
                "complexity_notes": "Simple implementation",
                "usage_examples": ["example()"],
                "design_patterns": [],
                "dependencies": []
            }
            
            mock_enricher = AsyncMock()
            mock_enricher_class.return_value.__aenter__.return_value = mock_enricher
            mock_enricher.enrich_entities.return_value = []
            
            # Run enrichment
            results = await enricher.enrich_files_inline(sample_entities, incremental=False)
            
            # Verify results
            assert len(results) > 0
            result = results[0]
            assert isinstance(result, InlineEnrichmentResult)
            assert result.file_path == str(sample_python_file)


class TestModuleEnrichmentGenerator:
    """Test module enrichment file generation."""
    
    def test_module_enrichment_generator_init(self, mock_config):
        """Test module enrichment generator initialization."""
        generator = ModuleEnrichmentGenerator(mock_config)
        assert generator.config == mock_config
    
    def test_get_module_entities(self, sample_entities, mock_config):
        """Test getting entities for a specific module."""
        generator = ModuleEnrichmentGenerator(mock_config)
        file_path = sample_entities[0].file_path
        
        entities = generator._get_module_entities(sample_entities, file_path)
        
        assert len(entities) == 3
        assert all(e.file_path == file_path for e in entities)
    
    def test_generate_module_overview(self, sample_entities, mock_config):
        """Test module overview generation."""
        generator = ModuleEnrichmentGenerator(mock_config)
        file_path = sample_entities[0].file_path
        
        overview = generator._generate_module_overview(file_path, sample_entities)
        
        assert overview["module_name"] == "sample"
        assert overview["file_path"] == file_path
        assert overview["total_entities"] == 3
        assert overview["functions"] == 2
        assert overview["classes"] == 1
        assert "last_updated" in overview
    
    def test_generate_markdown_enrichment(self, sample_entities, mock_config):
        """Test markdown enrichment generation."""
        generator = ModuleEnrichmentGenerator(mock_config)
        
        overview = {
            "module_name": "test_module",
            "file_path": "/test/path.py",
            "last_updated": "2024-01-01T00:00:00",
            "total_entities": 2,
            "functions": 1,
            "classes": 1
        }
        
        enriched_entities = [{
            "entity": sample_entities[0],
            "enrichment": {
                "description": "Test function",
                "purpose": "Testing",
                "key_features": ["Fast", "Simple"],
                "usage_examples": ["test()"]
            }
        }]
        
        markdown = generator._generate_markdown_enrichment(overview, enriched_entities, sample_entities)
        
        assert "# test_module - Module Enrichment" in markdown
        assert "**File:** `/test/path.py`" in markdown
        assert "### Function: `add_numbers`" in markdown
        assert "**Description:** Test function" in markdown
    
    def test_generate_json_enrichment(self, sample_entities, mock_config):
        """Test JSON enrichment generation."""
        generator = ModuleEnrichmentGenerator(mock_config)
        
        overview = {
            "module_name": "test_module",
            "file_path": "/test/path.py",
            "total_entities": 1
        }
        
        enriched_entities = [{
            "entity": sample_entities[0],
            "enrichment": {"description": "Test function"}
        }]
        
        json_content = generator._generate_json_enrichment(overview, enriched_entities, sample_entities)
        
        import json
        data = json.loads(json_content)
        
        assert data["overview"]["module_name"] == "test_module"
        assert len(data["enriched_entities"]) == 1
        assert data["enriched_entities"][0]["name"] == "add_numbers"