#!/usr/bin/env python3
"""
Tests for ChromaDB embedding functionality.
"""

import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from autodoc.analyzer import CodeEntity
from autodoc.chromadb_embedder import ChromaDBEmbedder


@pytest.fixture
def temp_dir():
    """Create a temporary directory for ChromaDB."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_entities():
    """Create sample code entities for testing."""
    return [
        CodeEntity(
            type="function",
            name="test_function",
            file_path="/test/path.py",
            line_number=10,
            docstring="Test function docstring",
            code="def test_function(): pass",
            embedding=None,
            is_internal=False
        ),
        CodeEntity(
            type="class",
            name="TestClass",
            file_path="/test/path.py",
            line_number=20,
            docstring="Test class docstring",
            code="class TestClass: pass",
            embedding=None,
            is_internal=True
        )
    ]


@pytest.mark.asyncio
async def test_chromadb_embedder_init(temp_dir):
    """Test ChromaDB embedder initialization."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir,
        embedding_model="all-MiniLM-L6-v2"
    )
    
    assert embedder.collection_name == "test_collection"
    assert str(embedder.persist_directory) == temp_dir
    assert embedder.embedding_model == "all-MiniLM-L6-v2"
    assert embedder.collection is not None


@pytest.mark.asyncio
async def test_embed_entities(temp_dir, sample_entities):
    """Test embedding entities."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    # Embed entities
    count = await embedder.embed_entities(sample_entities, use_enrichment=False)
    
    assert count == 2
    
    # Check that entities were added
    stats = embedder.get_stats()
    assert stats['total_embeddings'] == 2


@pytest.mark.asyncio
async def test_search_entities(temp_dir, sample_entities):
    """Test searching for entities."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    # Embed entities first
    await embedder.embed_entities(sample_entities, use_enrichment=False)
    
    # Search for function
    results = await embedder.search("test function", limit=5)
    
    assert len(results) > 0
    assert results[0]['entity']['name'] in ['test_function', 'TestClass']
    assert results[0]['similarity'] > 0


@pytest.mark.asyncio
async def test_clear_collection(temp_dir, sample_entities):
    """Test clearing the collection."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    # Embed entities
    await embedder.embed_entities(sample_entities, use_enrichment=False)
    
    # Clear collection
    embedder.clear_collection()
    
    # Check that collection is empty
    stats = embedder.get_stats()
    assert stats['total_embeddings'] == 0


@pytest.mark.asyncio
async def test_enriched_embedding(temp_dir, sample_entities):
    """Test embedding with enrichment cache."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    # Mock enrichment cache
    with patch('autodoc.chromadb_embedder.EnrichmentCache') as mock_cache_class:
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        
        # Mock enrichment data
        mock_cache.get_enrichment.return_value = {
            "description": "Enhanced description",
            "key_features": ["feature1", "feature2"],
            "purpose": "Test purpose"
        }
        
        # Embed with enrichment
        count = await embedder.embed_entities(sample_entities, use_enrichment=True)
        
        assert count == 2
        assert mock_cache.get_enrichment.called


def test_generate_id(temp_dir):
    """Test ID generation for entities."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    entity = CodeEntity(
        type="function",
        name="test_func",
        file_path="/path/to/file.py",
        line_number=42,
        docstring="",
        code="",
        embedding=None,
        is_internal=False
    )
    
    id1 = embedder.generate_id(entity)
    id2 = embedder.generate_id(entity)
    
    # Same entity should generate same ID
    assert id1 == id2
    assert len(id1) == 32  # MD5 hex length


def test_prepare_entity_text(temp_dir, sample_entities):
    """Test entity text preparation."""
    embedder = ChromaDBEmbedder(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    
    entity = sample_entities[0]
    text = embedder.prepare_entity_text(entity)
    
    assert "function test_function" in text
    assert "Test function docstring" in text
    assert "def test_function():" in text