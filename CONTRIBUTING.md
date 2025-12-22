# Contributing to Autodoc

Thank you for your interest in contributing to Autodoc! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Emberfield/autodoc.git
cd autodoc

# Setup development environment
make setup

# Activate virtual environment
source .venv/bin/activate

# Verify installation
autodoc --help
```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test
uv run pytest tests/test_autodoc.py::test_name -v

# Run with coverage
uv run pytest tests/ --cov=src/autodoc
```

### Code Formatting

We use `ruff` for linting and formatting:

```bash
# Format code
make format

# Or manually
uv run ruff check . --fix
uv run ruff format .
```

### Building

```bash
# Build package
make build

# Build will output to dist/
```

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Write clear, concise commit messages:

```
feat: Add semantic search to context packs
fix: Resolve embedding cache invalidation issue
docs: Update MCP server documentation
refactor: Simplify AST parsing logic
```

### Pull Request Process

1. Fork the repository and create your branch from `master`
2. Make your changes with appropriate tests
3. Ensure all tests pass: `make test`
4. Ensure code is formatted: `make format`
5. Update documentation if needed
6. Submit a pull request

### PR Checklist

- [ ] Tests added/updated for changes
- [ ] Documentation updated if needed
- [ ] Code formatted with `ruff`
- [ ] All tests passing
- [ ] Commit messages follow conventions

## Project Structure

```
autodoc/
├── src/autodoc/          # Main package
│   ├── cli.py           # CLI commands
│   ├── config.py        # Configuration management
│   ├── context_packs.py # Context pack functionality
│   ├── mcp_server.py    # MCP server implementation
│   └── ...
├── tests/               # Test suite
├── docs/                # Documentation
└── rust-core/           # Optional Rust analyzer
```

## Areas for Contribution

### Good First Issues

Look for issues labeled `good first issue` - these are great starting points.

### Feature Ideas

- Additional language support (JavaScript, Go, etc.)
- New MCP tools
- Visualization improvements
- Performance optimizations

### Documentation

- Improve README examples
- Add tutorials
- Document advanced features

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
