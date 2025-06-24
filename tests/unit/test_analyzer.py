#!/usr/bin/env python3
"""
Tests for the analyzer module
"""

import tempfile
from pathlib import Path

from autodoc.analyzer import CodeEntity, SimpleASTAnalyzer


class TestCodeEntity:
    """Test CodeEntity dataclass"""

    def test_code_entity_creation(self):
        entity = CodeEntity(
            type="function",
            name="test_func",
            file_path="/path/to/file.py",
            line_number=10,
            docstring="Test function",
            code="def test_func(): pass",
        )

        assert entity.type == "function"
        assert entity.name == "test_func"
        assert entity.line_number == 10
        assert entity.embedding is None

    def test_code_entity_with_embedding(self):
        embedding = [0.1, 0.2, 0.3]
        entity = CodeEntity(
            type="class",
            name="TestClass",
            file_path="/path/to/file.py",
            line_number=20,
            docstring="Test class",
            code="class TestClass:",
            embedding=embedding,
        )

        assert entity.embedding == embedding


class TestSimpleASTAnalyzer:
    """Test AST analyzer functionality"""

    def test_analyze_file(self, sample_python_file):
        analyzer = SimpleASTAnalyzer()
        entities = analyzer.analyze_file(sample_python_file)

        # Check we found all expected entities
        entity_names = [e.name for e in entities]
        assert "SampleClass" in entity_names
        assert "sample_function" in entity_names
        assert "async_function" in entity_names
        assert "_private_function" in entity_names
        assert "AbstractBase" in entity_names

        # Check entity types
        functions = [e for e in entities if e.type == "function"]
        classes = [e for e in entities if e.type == "class"]

        assert len(functions) >= 6  # Including class methods
        assert len(classes) == 2

        # Check docstrings were extracted
        sample_func = next(e for e in entities if e.name == "sample_function")
        assert sample_func.docstring is not None
        assert "processes data" in sample_func.docstring

    def test_analyze_invalid_file(self):
        analyzer = SimpleASTAnalyzer()
        entities = analyzer.analyze_file(Path("/nonexistent/file.py"))
        assert entities == []

    def test_analyze_syntax_error_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken_func( # syntax error")
            error_file = Path(f.name)

        try:
            analyzer = SimpleASTAnalyzer()
            entities = analyzer.analyze_file(error_file)
            assert entities == []
        finally:
            error_file.unlink()

    def test_async_function_detection(self, sample_python_file):
        """Test that async functions are properly detected"""
        analyzer = SimpleASTAnalyzer()
        entities = analyzer.analyze_file(sample_python_file)

        async_funcs = [e for e in entities if e.name == "async_function"]
        assert len(async_funcs) == 1

        # Check that the async function is properly marked
        async_func = async_funcs[0]
        assert async_func.type == "function"
        assert "async def" in async_func.code or async_func.code.startswith("async def")

    def test_class_method_detection(self, sample_python_file):
        """Test that class methods are properly detected"""
        analyzer = SimpleASTAnalyzer()
        entities = analyzer.analyze_file(sample_python_file)

        # Should find methods within classes
        method_names = [e.name for e in entities if e.type == "function"]
        assert "__init__" in method_names
        assert "upper_name" in method_names
        assert "static_method" in method_names
        assert "class_method" in method_names
