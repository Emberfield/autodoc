# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autodoc is an AI-powered code intelligence tool that analyzes Python codebases (for now) and enables semantic search using OpenAI embeddings. It parses Python files using AST (Abstract Syntax Tree) to extract functions and classes, then generates embeddings for intelligent code search.

## Project documentation

Since autodoc generates documentation for codebases, we have checked in documentation for this codebase itself:
`./comprehensive_data.json`
`./comprehensive_docs.md`

You should read these files to get an idea of how the project works and what files or functions you may need to change.

## Key Commands

### Development Environment

```bash
# Setup development environment with uv
make setup

# Activate virtual environment
source .venv/bin/activate

# Setup with graph dependencies (optional)
make setup-graph
```

### Common Tasks
```bash
# Analyze a codebase (with caching)
uv run python -m autodoc.cli analyze ./path/to/code --save
# or
make analyze

# Search analyzed code  
uv run python -m autodoc.cli search "query"
# or
make search QUERY="your query"

# Check configuration status
uv run python -m autodoc.cli check
# or
make check

# Run tests
uv run pytest tests/
# or
make test

# Format code
uv run black . && uv run ruff check . --fix
# or
make format

# Build package
uv build
# or
make build
```

### Graph Commands (Optional)
```bash
# Build code relationship graph
uv run python -m autodoc.cli build-graph --clear
# or
make build-graph

# Create visualizations
uv run python -m autodoc.cli visualize-graph --all
# or
make visualize-graph

# Query graph insights
uv run python -m autodoc.cli query-graph --all
# or
make query-graph
```

### Running Individual Tests
```bash
# Run specific test
uv run pytest tests/test_autodoc.py::test_ast_analyzer

# Run with verbose output
uv run pytest -v tests/

# Run core tests only
make test-core

# Run graph tests only (requires graph dependencies)
make test-graph
```

## Architecture

### Core Components

1. **SimpleASTAnalyzer** (src/autodoc/cli.py:35-64): Parses Python files to extract code entities (functions and classes) using Python's AST module.

2. **OpenAIEmbedder** (src/autodoc/cli.py:67-94): Handles embedding generation using OpenAI's text-embedding-3-small model for semantic search capabilities.

3. **SimpleAutodoc** (src/autodoc/cli.py:97-297): Main orchestrator that combines analysis and embedding to provide code intelligence features. Manages entity storage and search functionality.

4. **CLI Interface** (src/autodoc/cli.py:200-274): Click-based command-line interface providing analyze, search, and check commands.

### Data Flow

1. Analysis phase: Python files → AST parsing → CodeEntity objects → Optional embeddings generation → Cache storage (autodoc_cache.json)
2. Search phase: Load cache → Generate query embedding (if available) → Compute similarities → Return ranked results

### Key Design Decisions

- Uses dataclasses for clean entity representation
- Embeddings are optional - falls back to simple text search if OpenAI API key is not configured
- Results are cached in JSON format to avoid re-analysis
- Async operations for API calls (embedding generation)
- Rich console output for better user experience

## Configuration

- OpenAI API key should be set in `.env` file as `OPENAI_API_KEY=sk-...`
- The tool automatically loads environment variables using python-dotenv
- Cache is stored as `autodoc_cache.json` in the working directory

## Testing Strategy

Tests use pytest with pytest-asyncio for async test support. Tests create temporary files/directories to avoid side effects. Current test coverage includes AST analysis and basic autodoc functionality.