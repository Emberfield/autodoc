# Autodoc - AI-Powered Code Intelligence

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-Supported-007ACC.svg)](https://www.typescriptlang.org/)

Autodoc is an AI-powered code intelligence tool that analyzes Python and TypeScript codebases, enabling semantic search using OpenAI embeddings. It parses code using AST (Abstract Syntax Tree) analysis to extract functions, classes, and their relationships, then generates embeddings for intelligent code search.

## Features

- 🔍 **Semantic Code Search** - Search your codebase using natural language queries
- 🐍 **Python & TypeScript Support** - Full AST analysis for both languages
- 📊 **Comprehensive Analysis** - Extract and analyze functions, classes, and their relationships
- 🤖 **AI-Powered** - Optional OpenAI embeddings for enhanced search capabilities
- 📝 **Rich Documentation** - Generate detailed codebase documentation in Markdown or JSON
- 🚀 **Fast & Efficient** - Caches analysis results for quick repeated searches
- 🌐 **API Server** - REST API for integration with other tools
- 📈 **Graph Database** - Neo4j integration for relationship visualization
- 📦 **Easy Integration** - Use as CLI tool or Python library
- 🎨 **Beautiful Output** - Rich terminal UI with syntax highlighting

## Quick Start

```bash
# Install from private registry (for team members)
pip install --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/ autodoc

# Or install for development (requires uv)
git clone https://github.com/your-org/autodoc.git
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

# Additional commands
autodoc check                 # Check setup and configuration
autodoc graph --visualize     # Build graph database with visualizations
autodoc serve                 # Start REST API server
```

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

### OpenAI Integration (Optional)

For enhanced semantic search capabilities, set up OpenAI:

```bash
# Create .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

Autodoc works without OpenAI API key using simple text matching, but embeddings provide much better search results.

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
git clone https://github.com/your-org/autodoc.git
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
make publish        # Publish to GCP Artifact Registry

# Graph commands (require graph dependencies)
make build-graph    # Build code relationship graph
make visualize-graph # Create graph visualizations
make query-graph    # Query graph insights

# Quick workflows
make dev            # Quick development setup
make dev-graph      # Development setup with graph features
```

## Publishing & Deployment

Autodoc uses GCP Artifact Registry for private package hosting:

```bash
# One-time setup
make setup-gcp
make configure-auth

# Create a release
make release       # Interactive version bump
make publish       # Publish to registry

# Or use automated deployment
./scripts/deploy.sh patch  # or minor/major
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

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

- **Issues**: [GitHub Issues](https://github.com/your-org/autodoc/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md) for AI assistant guidance
- **Installation Help**: [INSTALL.md](INSTALL.md) for detailed setup instructions
