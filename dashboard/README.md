# Autodoc Dashboard

A web-based UI for exploring codebases analyzed with autodoc.

## Features

- **Overview**: Stats and summary of your analyzed codebase
- **Files**: Browse file tree with enrichment status indicators
- **Entities**: Search and filter functions, classes, and methods
- **Packs**: View context packs and their file patterns
- **Features**: Explore auto-detected code clusters
- **Search**: Semantic search interface (connects to CLI)

## Quick Start

```bash
# From the autodoc root directory
make dashboard

# Or manually
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000

## Prerequisites

The dashboard reads data from autodoc cache files. Make sure you've analyzed your codebase first:

```bash
# Analyze your code
autodoc analyze . --save

# Optional: Generate context packs
autodoc pack auto-generate --save

# Optional: AI enrichment (requires API key)
autodoc enrich --inline --limit 50

# Optional: Feature detection (requires Neo4j)
autodoc graph --clear
autodoc features detect
autodoc features name
```

## Data Sources

The dashboard reads from these files in your project root:

| File | Description |
|------|-------------|
| `autodoc_cache.json` | Analysis results (entities, files) |
| `autodoc_enrichment_cache.json` | AI-generated documentation |
| `.autodoc.yaml` | Configuration and context packs |
| `.autodoc/features_cache.json` | Detected code features |

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS v4
- **Components**: shadcn/ui
- **Icons**: Lucide React

## Roadmap

- [ ] Real-time semantic search (connect to ChromaDB)
- [ ] Entity detail modal with full AI docs
- [ ] Dependency graph visualization
- [ ] Feature cluster visualization
- [ ] Cloud hosting with auth
