# FastAPI Demo - Autodoc in Action

This demo showcases autodoc's full feature set by analyzing the [FastAPI](https://github.com/tiangolo/fastapi) framework.

## Quick Start

```bash
# From the autodoc root directory
cd examples/fastapi-demo
./demo.sh
```

## What the Demo Shows

### 1. Codebase Analysis
Extracts all Python functions, classes, decorators, and their relationships using AST parsing.

```bash
autodoc analyze ./fastapi --save
```

### 2. Context Pack Generation
Automatically detects logical code groupings based on directory structure and naming patterns.

```bash
autodoc pack auto-generate --save
autodoc pack list
```

### 3. Semantic Search
Search across the codebase using natural language queries.

```bash
autodoc search "dependency injection"
autodoc search "request validation"
autodoc pack query routing "how does URL routing work"
```

### 4. AI Enrichment (Optional)
Generate detailed documentation for functions and classes using LLMs.

```bash
# Requires ANTHROPIC_API_KEY or OPENAI_API_KEY
autodoc enrich --inline --limit 10
```

### 5. Feature Detection (Optional)
Use graph analysis to discover code clusters and name them semantically.

```bash
# Requires Neo4j with GDS plugin
autodoc graph --clear
autodoc features detect
autodoc features name
autodoc features list
```

### 6. Dashboard UI
After analysis, the demo launches an interactive web dashboard to explore results.

```bash
# Dashboard opens automatically at http://localhost:3000
# Or start manually:
make dashboard
```

The dashboard shows:
- **Overview**: Stats and summary cards
- **Files**: Browsable file tree with enrichment indicators
- **Entities**: Searchable list of functions and classes
- **Packs**: Context pack details and file patterns
- **Features**: Auto-detected code clusters

## Sample Output

After running the demo, you'll have:

```
fastapi-repo/
├── .autodoc.yaml          # Configuration with auto-detected packs
├── autodoc_cache.json     # Analysis results
├── autodoc_enrichment_cache.json  # AI-generated docs (if enriched)
└── .autodoc/
    └── features_cache.json  # Detected features (if Neo4j used)
```

## Manual Step-by-Step

If you prefer to run commands manually:

```bash
# 1. Clone FastAPI
git clone --depth 1 https://github.com/tiangolo/fastapi.git
cd fastapi

# 2. Analyze
autodoc analyze ./fastapi --save

# 3. Generate packs
autodoc pack auto-generate --save

# 4. Explore
autodoc pack list
autodoc pack info routing
autodoc search "middleware"

# 5. Build embeddings for better search
autodoc pack build --all --embeddings

# 6. Query with vectors
autodoc pack query security "authentication flow"
```

## MCP Integration

Start the MCP server to integrate with AI assistants:

```bash
autodoc mcp-server
```

Available tools:
- `pack_list` - List all context packs
- `pack_query` - Semantic search within a pack
- `pack_files` - Get files in a pack
- `impact_analysis` - Analyze change impact
- `feature_list` - List detected features
- `feature_files` - Get files in a feature

## Requirements

- Python 3.10+
- `pip install ai-code-autodoc`
- (Optional) `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for enrichment
- (Optional) Neo4j with GDS plugin for feature detection
