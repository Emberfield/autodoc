# Testing Guide

This document explains the modular test structure for Autodoc and how to work with tests effectively.

## Test Structure

The test suite has been organized into a modular structure that mirrors the source code organization:

```
tests/
├── conftest.py                 # Shared fixtures and test utilities
├── unit/                       # Unit tests for individual modules
│   ├── __init__.py
│   ├── test_analyzer.py       # Tests for analyzer.py
│   ├── test_embedder.py       # Tests for embedder.py
│   ├── test_autodoc.py        # Tests for autodoc.py
│   └── test_cli.py            # Tests for cli.py
├── integration/                # End-to-end integration tests
│   ├── __init__.py
│   └── test_end_to_end.py     # Full workflow tests
└── test_graph.py              # Graph functionality tests (optional dependencies)
```

## Running Tests

### All Tests
```bash
make test                    # Run all tests
hatch run pytest tests/     # Alternative using hatch directly
```

### Unit Tests
```bash
make test-unit              # Run all unit tests
make test-analyzer          # Run analyzer tests only
make test-embedder          # Run embedder tests only
make test-autodoc           # Run autodoc tests only
make test-cli               # Run CLI tests only
```

### Integration Tests
```bash
make test-integration       # Run integration tests
```

### Specific Test Files
```bash
hatch run pytest tests/unit/test_analyzer.py -v
hatch run pytest tests/integration/test_end_to_end.py::TestEndToEndWorkflow::test_full_cli_workflow -v
```

### Test Coverage
```bash
make test-coverage          # Run with coverage report
```

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation
- Fast execution
- Mock external dependencies
- Focus on single responsibility

**Files**:
- `test_analyzer.py` - Tests for AST analysis and CodeEntity creation
- `test_embedder.py` - Tests for OpenAI embedding functionality
- `test_autodoc.py` - Tests for main SimpleAutodoc class
- `test_cli.py` - Tests for CLI commands and interface

### Integration Tests (`tests/integration/`)

**Purpose**: Test complete workflows and component interactions
- Test end-to-end functionality
- Verify system behavior
- Test error handling across components

**Files**:
- `test_end_to_end.py` - Complete workflow tests (analyze → search → generate)

### Graph Tests (`tests/test_graph.py`)

**Purpose**: Test optional graph functionality
- Most tests are skipped if dependencies aren't available
- Tests graceful degradation when Neo4j/matplotlib aren't installed

## Test Fixtures

Shared fixtures are defined in `tests/conftest.py`:

- `sample_python_file` - Creates a temporary Python file with various code constructs
- `sample_test_file` - Creates a sample test file
- `sample_project_dir` - Creates a complete project structure for testing
- `sample_code_entities` - Pre-built CodeEntity objects for testing

## Writing New Tests

### 1. Choose the Right Location

- **Unit tests**: Add to `tests/unit/test_<module>.py`
- **Integration tests**: Add to `tests/integration/`
- **New test files**: Follow naming convention `test_<feature>.py`

### 2. Use Appropriate Fixtures

```python
def test_my_feature(sample_project_dir, monkeypatch):
    # Use shared fixtures from conftest.py
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # ... test code
```

### 3. Follow Testing Patterns

**Unit Test Example**:
```python
class TestMyComponent:
    """Test MyComponent functionality"""
    
    def test_basic_functionality(self):
        component = MyComponent()
        result = component.process("input")
        assert result == "expected_output"
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        component = MyComponent()
        result = await component.async_process("input")
        assert result is not None
```

**Mock External Dependencies**:
```python
@pytest.mark.asyncio
async def test_with_mocked_api(self):
    with patch("autodoc.embedder.OpenAIEmbedder.embed") as mock_embed:
        mock_embed.return_value = [0.1, 0.2, 0.3]
        # ... test code
```

## Testing Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names
- Add docstrings for complex tests

### 2. Isolation
- Tests should not depend on each other
- Use fixtures for setup/teardown
- Clean up temporary files

### 3. Mocking
- Mock external API calls (OpenAI, etc.)
- Mock file system operations when appropriate
- Use `monkeypatch` for environment variables

### 4. Async Testing
- Use `@pytest.mark.asyncio` for async tests
- Mock async dependencies properly
- Test both success and error cases

## Common Testing Scenarios

### Testing CLI Commands
```python
def test_cli_command(self):
    runner = CliRunner()
    result = runner.invoke(cli, ["command", "args"])
    assert result.exit_code == 0
    assert "expected output" in result.output
```

### Testing File Analysis
```python
def test_file_analysis(self, sample_python_file):
    analyzer = SimpleASTAnalyzer()
    entities = analyzer.analyze_file(sample_python_file)
    assert len(entities) > 0
    assert any(e.name == "expected_function" for e in entities)
```

### Testing Search Functionality
```python
@pytest.mark.asyncio
async def test_search(self, sample_code_entities):
    autodoc = SimpleAutodoc()
    autodoc.entities = sample_code_entities
    results = await autodoc.search("query", limit=5)
    assert len(results) > 0
```

## Debugging Tests

### Run with Verbose Output
```bash
hatch run pytest tests/unit/test_analyzer.py -v -s
```

### Run Single Test
```bash
hatch run pytest tests/unit/test_analyzer.py::TestSimpleASTAnalyzer::test_analyze_file -v
```

### Debug with Breakpoints
```python
def test_my_feature():
    import pdb; pdb.set_trace()  # Add breakpoint
    # ... test code
```

## Continuous Integration

The test suite is designed to run in CI environments:
- All tests should pass without external dependencies
- Graph tests are skipped when optional dependencies are missing
- Use environment variables for configuration
- Temporary files are cleaned up automatically

## Performance Testing

For performance-sensitive code:
- Use `tests/integration/test_end_to_end.py::test_large_codebase_performance`
- Monitor test execution time
- Add performance regression tests when needed

## Adding Test Dependencies

Add test-only dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",  # For coverage
    # ... other test dependencies
]
```

## Summary

The modular test structure provides:
- ✅ **Clear organization** matching source code structure
- ✅ **Fast unit tests** for rapid development feedback
- ✅ **Comprehensive integration tests** for system validation
- ✅ **Flexible test execution** with granular control
- ✅ **Easy test discovery** and maintenance
- ✅ **Consistent patterns** for new test development

This structure scales well as the codebase grows and makes it easy for team members to find and run relevant tests.