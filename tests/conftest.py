#!/usr/bin/env python3
"""
Shared test fixtures for Autodoc test suite
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_python_file():
    """Create a sample Python file for testing"""
    content = '''#!/usr/bin/env python3
"""
Sample module for testing autodoc.
"""

import os
import json
from typing import List, Dict

class SampleClass:
    """A sample class for testing."""
    
    def __init__(self, name: str):
        """Initialize the sample class."""
        self.name = name
    
    @property
    def upper_name(self) -> str:
        """Get uppercase name."""
        return self.name.upper()
    
    @staticmethod
    def static_method():
        """A static method."""
        return "static"
    
    @classmethod
    def class_method(cls):
        """A class method."""
        return cls.__name__

def sample_function(param1: str, param2: int = 10) -> Dict[str, any]:
    """
    A sample function that processes data.
    
    Args:
        param1: First parameter
        param2: Second parameter with default
        
    Returns:
        A dictionary with results
    """
    return {"param1": param1, "param2": param2}

async def async_function():
    """An async function for testing."""
    return await some_async_call()

def _private_function():
    """A private function."""
    pass

class AbstractBase:
    """Abstract base class."""
    
    def abstract_method(self):
        raise NotImplementedError
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        return Path(f.name)


@pytest.fixture
def sample_test_file():
    """Create a sample test file"""
    content = '''import pytest

def test_something():
    """Test something."""
    assert True

def test_another_thing():
    """Test another thing."""
    assert 1 + 1 == 2
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix="_test.py", delete=False) as f:
        f.write(content)
        return Path(f.name)


@pytest.fixture
def sample_project_dir(sample_python_file, sample_test_file):
    """Create a sample project directory structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create directory structure
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()
        (project_dir / "src" / "__init__.py").touch()

        # Copy files
        (project_dir / "src" / "module.py").write_text(sample_python_file.read_text())
        (project_dir / "tests" / "test_module.py").write_text(sample_test_file.read_text())

        # Create config file
        (project_dir / "config.py").write_text(
            '''
"""Configuration module."""
DEBUG = True
API_KEY = "test-key"
'''
        )

        yield project_dir

        # Cleanup
        sample_python_file.unlink()
        sample_test_file.unlink()


@pytest.fixture
def sample_code_entities():
    """Sample CodeEntity objects for testing"""
    from autodoc.analyzer import CodeEntity

    return [
        CodeEntity(
            type="function",
            name="process_data",
            file_path="/test.py",
            line_number=1,
            docstring="Process the data",
            code="def process_data(): pass",
            embedding=[0.9, 0.1],
        ),
        CodeEntity(
            type="function",
            name="save_file",
            file_path="/test.py",
            line_number=10,
            docstring="Save to file",
            code="def save_file(): pass",
            embedding=[0.1, 0.9],
        ),
        CodeEntity(
            type="class",
            name="TestClass",
            file_path="/test.py",
            line_number=20,
            docstring="Test class",
            code="class TestClass:",
            embedding=[0.5, 0.5],
        ),
    ]
