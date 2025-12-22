# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autodoc is an AI-powered code intelligence tool that analyzes Python and TypeScript codebases, enabling semantic search using local ChromaDB embeddings or OpenAI. It parses code using AST analysis to extract functions and classes, groups them into context packs for feature-based organization, and provides an MCP server for AI assistant integration.

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

### Context Pack Commands
```bash
# Auto-detect and suggest packs based on codebase structure
autodoc pack auto-generate --save

# List all defined context packs
autodoc pack list

# Build a pack with embeddings (for semantic search)
autodoc pack build auth --embeddings

# Build all packs with AI summaries
autodoc pack build --all --embeddings --summary

# Search within a specific pack
autodoc pack query auth "user authentication flow"

# Check what changed since last index
autodoc pack diff auth

# Show pack dependencies
autodoc pack deps auth --transitive

# Check indexing status
autodoc pack status
```

### Impact Analysis
```bash
# Analyze how file changes affect context packs
autodoc impact api/auth.py api/users.py --json
```

### MCP Server
```bash
# Start MCP server for AI assistant integration
autodoc mcp-server

# Available tools: pack_list, pack_info, pack_query, pack_files,
# pack_entities, impact_analysis, pack_status, pack_deps, pack_diff
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

1. **SimpleASTAnalyzer** (src/autodoc/analyzer.py): Parses Python files to extract code entities (functions and classes) using Python's AST module.

2. **ChromaDBEmbedder** (src/autodoc/chromadb_embedder.py): Handles embedding generation using local sentence-transformers for free semantic search.

3. **SimpleAutodoc** (src/autodoc/cli.py): Main orchestrator that combines analysis and embedding. Manages entity storage and search functionality.

4. **AutodocConfig** (src/autodoc/config.py): Pydantic-based configuration with LLMConfig, EmbeddingsConfig, CostControlConfig, and ContextPackConfig.

5. **MCP Server** (src/autodoc/mcp_server.py): FastMCP-based server providing 9 tools for AI assistant integration.

6. **CLI Interface** (src/autodoc/cli.py): Click-based command-line interface with commands for analyze, search, pack management, and impact analysis.

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

Configuration is stored in `.autodoc.yaml`:

```yaml
llm:
  provider: anthropic  # or openai, ollama
  model: claude-sonnet-4-20250514

embeddings:
  provider: chromadb  # Free local embeddings, no API key needed
  chromadb_model: all-MiniLM-L6-v2

cost_control:
  summary_model: claude-3-haiku-20240307  # Cheaper model for pack summaries
  cache_summaries: true
  warn_entity_threshold: 100

context_packs:
  - name: auth
    display_name: Authentication
    files: ["src/auth/**/*.py"]
    security_level: critical
```

API keys (optional, for LLM features):
- `ANTHROPIC_API_KEY` for Claude-based enrichment/summaries
- `OPENAI_API_KEY` for OpenAI-based enrichment

## Testing Strategy

Tests use pytest with pytest-asyncio for async test support. Tests create temporary files/directories to avoid side effects. Current test coverage includes AST analysis and basic autodoc functionality.