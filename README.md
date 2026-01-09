# Autodoc - AI-Powered Code Intelligence

[![PyPI version](https://badge.fury.io/py/ai-code-autodoc.svg)](https://pypi.org/project/ai-code-autodoc/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-Supported-007ACC.svg)](https://www.typescriptlang.org/)

Autodoc is an AI-powered code intelligence tool that analyzes Python and TypeScript codebases, enabling semantic search using OpenAI embeddings. It parses code using AST (Abstract Syntax Tree) analysis to extract functions, classes, and their relationships, then generates embeddings for intelligent code search.

## Features

- 🔍 **Semantic Code Search** - Search your codebase using natural language queries
- 🐍 **Python & TypeScript Support** - Full AST analysis for both languages
- 📊 **Comprehensive Analysis** - Extract and analyze functions, classes, and their relationships
- 🤖 **AI-Powered** - Optional OpenAI embeddings for enhanced search capabilities
- 🧠 **LLM Code Enrichment** - Generate detailed descriptions using OpenAI, Anthropic/Claude, or Ollama
- 📝 **Rich Documentation** - Generate detailed codebase documentation in Markdown or JSON
- 🚀 **Fast & Efficient** - Caches analysis results for quick repeated searches
- 🌐 **API Server** - REST API for integration with other tools
- 📈 **Graph Database** - Neo4j integration for relationship visualization
- 📦 **Easy Integration** - Use as CLI tool or Python library
- 🎨 **Beautiful Output** - Rich terminal UI with syntax highlighting

## Quick Start

```bash
# Install from PyPI
pip install ai-code-autodoc

# Or install for development (requires uv)
git clone https://github.com/Emberfield/autodoc.git
cd autodoc
make setup
source .venv/bin/activate
```

## Basic Usage

### Command Line

```bash
# Quick workflow
autodoc analyze ./src          # Analyze your codebase
autodoc generate              # Create AUTODOC.md documentation
autodoc vector                # Generate embeddings for search  
autodoc search "auth logic"   # Search with natural language

# LLM Enrichment (NEW!)
autodoc init                  # Create .autodoc.yml config
autodoc enrich --limit 50     # Enrich code with AI descriptions
autodoc generate              # Now includes enriched content!

# Additional commands
autodoc check                 # Check setup and configuration
autodoc graph --visualize     # Build graph database with visualizations
autodoc serve                 # Start REST API server
```

### Context Packs

Context packs group related code by feature for focused search and AI context:

```bash
# Auto-detect and suggest packs based on codebase structure
autodoc pack auto-generate --save

# List all defined packs
autodoc pack list

# Build pack with embeddings for semantic search
autodoc pack build auth --embeddings

# Build all packs with AI summaries (requires API key)
autodoc pack build --all --embeddings --summary

# Search within a specific pack
autodoc pack query auth "user login flow"

# See pack dependencies
autodoc pack deps auth --transitive

# Check what changed since last index
autodoc pack diff auth
```

### Impact Analysis

Analyze how file changes affect your codebase:

```bash
# Analyze impact of changed files
autodoc impact api/auth.py api/users.py --json

# Check pack indexing status
autodoc pack status
```

### MCP Server

Autodoc includes an MCP (Model Context Protocol) server for AI assistant integration:

```bash
# Start MCP server
autodoc mcp-server
```

**Available MCP Tools:**

*Core Tools (always available):*
- `capabilities` - Check what tools are available based on your setup
- `pack_list` - List all context packs
- `pack_info` - Get details about a pack
- `pack_query` - Semantic search within a pack
- `pack_files` - List files in a pack
- `pack_entities` - List code entities in a pack
- `impact_analysis` - Analyze file change impact
- `pack_status` - Get indexing status
- `pack_deps` - Get pack dependencies
- `pack_diff` - Check what changed since last index
- `analyze` - Analyze codebase and extract entities
- `search` - Semantic search across codebase
- `generate` - Generate documentation

*Graph Tools (require Neo4j - see setup below):*
- `graph_build` - Build code relationship graph
- `graph_query` - Query graph for insights
- `feature_list` - List auto-detected code features
- `feature_files` - Get files in a feature cluster

**Tip:** Call the `capabilities` tool first to see which tools are available in your environment.

### Web Dashboard

Autodoc includes a web-based dashboard for exploring your analyzed codebase:

```bash
# From the autodoc root directory
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000 to view:
- **Overview**: Stats and summary of your analyzed codebase
- **Files**: Browse file tree with enrichment status indicators
- **Entities**: Search and filter functions, classes, and methods
- **Packs**: View context packs and their file patterns
- **Features**: Explore auto-detected code clusters
- **Search**: Semantic search interface

**Prerequisites**: The dashboard reads from autodoc cache files. Run `autodoc analyze . --save` first.

See [dashboard/README.md](dashboard/README.md) for more details.

### Python API

```python
from autodoc import SimpleAutodoc
import asyncio

async def main():
    # Initialize autodoc
    autodoc = SimpleAutodoc()
    
    # Analyze a directory
    summary = await autodoc.analyze_directory("./src")
    print(f"Found {summary['total_entities']} code entities")
    
    # Search with natural language
    results = await autodoc.search("validation logic", limit=5)
    for result in results:
        print(f"{result['entity']['name']} - {result['similarity']:.2f}")

asyncio.run(main())
```

## Configuration

Create a `.autodoc.yml` file in your project root (or run `autodoc init`):

```yaml
# LLM provider settings
llm:
  provider: anthropic  # or openai, ollama
  model: claude-sonnet-4-20250514
  temperature: 0.3

# Embeddings - use chromadb for free local embeddings
embeddings:
  provider: chromadb
  chromadb_model: all-MiniLM-L6-v2
  dimensions: 384

# Cost controls for LLM operations
cost_control:
  summary_model: claude-3-haiku-20240307  # Cheaper model for summaries
  warn_entity_threshold: 100              # Warn on large packs
  cache_summaries: true                   # Cache to avoid regenerating
  dry_run_by_default: false

# Context packs for feature-based code grouping
context_packs:
  - name: auth
    display_name: Authentication
    description: User authentication and authorization
    files:
      - "src/auth/**/*.py"
      - "api/routes/auth.py"
    security_level: critical
    tags: [security, core]
```

### API Keys (Optional)

For LLM-powered features (enrichment, summaries):

```bash
# Anthropic (recommended for summaries)
export ANTHROPIC_API_KEY=sk-ant-...

# Or OpenAI
export OPENAI_API_KEY=sk-...
```

Note: Embeddings use local ChromaDB by default - no API key needed for semantic search!

## Development

### Prerequisites

First, install [uv](https://docs.astral.sh/uv/) - the fast Python package manager:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Emberfield/autodoc.git
cd autodoc

# Setup environment with uv
make setup

# Activate virtual environment
source .venv/bin/activate

# Run tests
make test

# Format code
make format

# Build package
make build
```

### Available Make Commands

```bash
make help           # Show all available commands
make setup          # Setup development environment with uv
make setup-graph    # Setup with graph dependencies
make analyze        # Analyze current directory
make search QUERY="your search"  # Search code
make test           # Run all tests
make test-core      # Run core tests only
make test-graph     # Run graph tests only
make lint           # Check code quality
make format         # Format code
make build          # Build package

# Graph commands (require graph dependencies)
make build-graph    # Build code relationship graph
make visualize-graph # Create graph visualizations
make query-graph    # Query graph insights

# Quick workflows
make dev            # Quick development setup
make dev-graph      # Development setup with graph features
```

## Publishing & Deployment

Autodoc is published to PyPI with automated releases via GitHub Actions:

```bash
# Build package locally
make build

# Create a GitHub release to trigger automatic PyPI publish
# Or manually trigger the workflow from GitHub Actions
```

The package is available at [pypi.org/project/ai-code-autodoc](https://pypi.org/project/ai-code-autodoc/).

## Architecture

### Core Components

- **SimpleASTAnalyzer** - Parses Python files using AST to extract code entities
- **OpenAIEmbedder** - Handles embedding generation for semantic search
- **SimpleAutodoc** - Main orchestrator combining analysis and search
- **CLI Interface** - Rich command-line interface built with Click

### Data Flow

1. **Analysis Phase**: Python files → AST parsing → CodeEntity objects → Optional embeddings → Cache
2. **Search Phase**: Query → Embedding (if available) → Similarity computation → Ranked results

## Advanced Features

### Generate Comprehensive Documentation

```bash
# Generate markdown documentation
autodoc generate-summary --format markdown --output codebase-docs.md

# Generate JSON for programmatic use
autodoc generate-summary --format json --output codebase-data.json
```

### Code Graph Analysis (Optional)

With additional dependencies, you can build and query a code relationship graph:

```bash
# Setup with graph dependencies
make setup-graph
source .venv/bin/activate

# Build graph (requires Neo4j running)
autodoc build-graph --clear

# Create visualizations
autodoc visualize-graph --all

# Query insights
autodoc query-graph --all

# Or use make commands
make build-graph
make visualize-graph
make query-graph
```

#### Neo4j Setup

The graph features require a running Neo4j instance with the Graph Data Science (GDS) plugin.

**Quick Start with Docker Compose:**

```bash
# Start Neo4j with GDS plugin
docker compose up -d

# Verify it's running
docker compose ps

# View logs
docker compose logs -f neo4j
```

After starting, Neo4j will be available at:
- Browser UI: http://localhost:7474
- Bolt protocol: bolt://localhost:7687
- Default credentials: `neo4j` / `autodoc123`

**Manual Docker Setup:**

```bash
docker run -d \
  --name autodoc-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/autodoc123 \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=gds.* \
  neo4j:5-community
```

**Configure environment:**

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=autodoc123
```

#### Graph Dependencies

The graph features require additional packages:
- `neo4j` - Graph database driver
- `matplotlib` - Static graph visualization
- `networkx` - Graph analysis
- `plotly` - Interactive visualizations
- `pyvis` - Interactive network graphs

Install them with: `make setup-graph` or `uv sync --extra graph`

## Example Output

### Search Results
```
Search Results for 'authentication'
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Type     ┃ Name           ┃ File                ┃ Line      ┃ Similarity ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ function │ authenticate   │ auth/handler.py     │ 45        │ 0.92       │
│ class    │ AuthManager    │ auth/manager.py     │ 12        │ 0.87       │
│ function │ check_token    │ auth/tokens.py      │ 78        │ 0.83       │
└──────────┴────────────────┴─────────────────────┴───────────┴────────────┘
```

### Analysis Summary
```
Analysis Summary:
  files_analyzed: 42
  total_entities: 237
  functions: 189
  classes: 48
  has_embeddings: True
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Format code (`make format`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/Emberfield/autodoc/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md) for AI assistant guidance
- **PyPI Package**: [ai-code-autodoc](https://pypi.org/project/ai-code-autodoc/)
