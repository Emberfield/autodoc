"""
Test cache loading compatibility to prevent breaking changes.
"""

import json
import tempfile
from pathlib import Path

import pytest

from autodoc.analyzer import CodeEntity
from autodoc.autodoc import SimpleAutodoc


class TestCacheCompatibility:
    """Test that cache files with extra fields can still be loaded."""
    
    def test_load_cache_with_extra_fields(self):
        """Test loading cache with fields that don't exist in current CodeEntity."""
        # Create a cache file with extra fields (simulating older/newer versions)
        cache_data = {
            "entities": [
                {
                    "type": "function",
                    "name": "test_function",
                    "file_path": "test.py",
                    "line_number": 10,
                    "docstring": "Test function",
                    "code": "def test_function(): pass",
                    "embedding": None,
                    "decorators": [],
                    "http_methods": [],
                    "route_path": None,
                    "is_internal": True,
                    # Extra fields that might exist in cache but not in current version
                    "is_async": True,  # This was causing the bug
                    "parameters": ["arg1", "arg2"],
                    "return_type": "str",
                    "complexity": 5,
                    "future_field": "some_value"
                },
                {
                    "type": "class",
                    "name": "TestClass",
                    "file_path": "test.py", 
                    "line_number": 20,
                    "docstring": "Test class",
                    "code": "class TestClass: pass",
                    "embedding": [0.1, 0.2, 0.3],
                    "decorators": ["@dataclass"],
                    "http_methods": [],
                    "route_path": None,
                    "is_internal": False,
                    # More extra fields
                    "base_classes": ["BaseClass"],
                    "methods": ["method1", "method2"],
                    "is_abstract": False
                }
            ]
        }
        
        # Write cache to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(cache_data, f)
            cache_path = f.name
        
        try:
            # Load cache with SimpleAutodoc
            autodoc = SimpleAutodoc()
            autodoc.load(cache_path)
            
            # Verify entities were loaded correctly
            assert len(autodoc.entities) == 2
            
            # Check first entity
            entity1 = autodoc.entities[0]
            assert entity1.type == "function"
            assert entity1.name == "test_function"
            assert entity1.file_path == "test.py"
            assert entity1.line_number == 10
            assert entity1.docstring == "Test function"
            assert entity1.code == "def test_function(): pass"
            assert entity1.embedding is None
            assert entity1.decorators == []
            assert entity1.http_methods == []
            assert entity1.route_path is None
            assert entity1.is_internal is True
            
            # Check second entity
            entity2 = autodoc.entities[1]
            assert entity2.type == "class"
            assert entity2.name == "TestClass"
            assert entity2.file_path == "test.py"
            assert entity2.line_number == 20
            assert entity2.docstring == "Test class"
            assert entity2.code == "class TestClass: pass"
            assert entity2.embedding == [0.1, 0.2, 0.3]
            assert entity2.decorators == ["@dataclass"]
            assert entity2.is_internal is False
            
            # Verify extra fields were ignored and didn't cause errors
            # The entities should only have fields defined in CodeEntity
            assert not hasattr(entity1, 'is_async')  # This should be filtered out
            assert not hasattr(entity1, 'return_type')  # This should be filtered out
            assert not hasattr(entity1, 'complexity')  # This should be filtered out 
            assert not hasattr(entity1, 'future_field')  # This should be filtered out
            assert not hasattr(entity2, 'base_classes')  # This should be filtered out
            assert not hasattr(entity2, 'methods')  # This should be filtered out
            assert not hasattr(entity2, 'is_abstract')  # This should be filtered out
            
            # parameters field exists in CodeEntity but might have wrong type
            assert hasattr(entity1, 'parameters')  # This is a valid field
            
        finally:
            # Clean up
            Path(cache_path).unlink()
    
    def test_load_cache_missing_required_fields(self):
        """Test loading cache with missing required fields fails gracefully."""
        # Create a cache file with missing required fields
        cache_data = {
            "entities": [
                {
                    # Missing required fields: type, name, file_path, line_number, code
                    "docstring": "Incomplete entity",
                    "embedding": None
                }
            ]
        }
        
        # Write cache to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(cache_data, f)
            cache_path = f.name
        
        try:
            # Load cache should fail but not crash
            autodoc = SimpleAutodoc()
            with pytest.raises(TypeError) as exc_info:
                autodoc.load(cache_path)
            
            # Verify it's complaining about missing required fields
            assert "missing" in str(exc_info.value) or "required" in str(exc_info.value)
            
        finally:
            # Clean up
            Path(cache_path).unlink()
            
    def test_save_and_load_cycle(self):
        """Test that save and load cycle preserves all CodeEntity fields."""
        # Create entities
        entity1 = CodeEntity(
            type="function",
            name="save_test",
            file_path="save_test.py",
            line_number=5,
            docstring="Save test function",
            code="def save_test(): return True",
            embedding=[0.5, 0.6, 0.7],
            decorators=["@pytest.fixture"],
            http_methods=["GET", "POST"],
            route_path="/api/test",
            is_internal=False
        )
        
        entity2 = CodeEntity(
            type="class",
            name="SaveTestClass",
            file_path="save_test.py",
            line_number=15,
            docstring=None,
            code="class SaveTestClass: pass",
            embedding=None,
            decorators=[],
            http_methods=[],
            route_path=None,
            is_internal=True
        )
        
        # Save entities
        autodoc1 = SimpleAutodoc()
        autodoc1.entities = [entity1, entity2]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_path = f.name
        
        try:
            autodoc1.save(cache_path)
            
            # Load entities
            autodoc2 = SimpleAutodoc()
            autodoc2.load(cache_path)
            
            # Verify all fields are preserved
            assert len(autodoc2.entities) == 2
            
            loaded1 = autodoc2.entities[0]
            assert loaded1.type == entity1.type
            assert loaded1.name == entity1.name
            assert loaded1.file_path == entity1.file_path
            assert loaded1.line_number == entity1.line_number
            assert loaded1.docstring == entity1.docstring
            assert loaded1.code == entity1.code
            assert loaded1.embedding == entity1.embedding
            assert loaded1.decorators == entity1.decorators
            assert loaded1.http_methods == entity1.http_methods
            assert loaded1.route_path == entity1.route_path
            assert loaded1.is_internal == entity1.is_internal
            
            loaded2 = autodoc2.entities[1]
            assert loaded2.type == entity2.type
            assert loaded2.name == entity2.name
            assert loaded2.file_path == entity2.file_path
            assert loaded2.line_number == entity2.line_number
            assert loaded2.docstring == entity2.docstring
            assert loaded2.code == entity2.code
            assert loaded2.embedding == entity2.embedding
            assert loaded2.decorators == entity2.decorators
            assert loaded2.http_methods == entity2.http_methods
            assert loaded2.route_path == entity2.route_path
            assert loaded2.is_internal == entity2.is_internal
            
        finally:
            # Clean up
            Path(cache_path).unlink()