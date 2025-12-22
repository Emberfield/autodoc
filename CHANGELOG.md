# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] - 2024-12-22

### Added
- **Context Packs**: Feature-based code grouping for focused search and AI context
  - `pack list` - List all defined packs
  - `pack info <name>` - Get detailed pack information
  - `pack build <name>` - Build pack with embeddings and optional summaries
  - `pack query <name> <query>` - Semantic search within a pack
  - `pack auto-generate` - Auto-detect packs from codebase structure
  - `pack diff <name>` - Show changes since last index
  - `pack deps <name>` - Show pack dependencies
  - `pack status` - Show indexing status for all packs
- **Impact Analysis**: `autodoc impact <files>` to analyze how file changes affect packs
- **MCP Server**: 9 tools for AI assistant integration via Model Context Protocol
  - pack_list, pack_info, pack_query, pack_files, pack_entities
  - impact_analysis, pack_status, pack_deps, pack_diff
- **Cost Controls**: Features to manage LLM API costs
  - `--dry-run` flag to preview operations without API calls
  - `summary_model` config to use cheaper models for summaries
  - `cache_summaries` to avoid regenerating unchanged content
  - Token logging for cost visibility
- **ChromaDB Provider**: Free local embeddings with sentence-transformers
- **PyPI Publishing**: Package now available via `pip install ai-code-autodoc`
- **--root flag**: For `pack auto-generate` to specify base directory (useful in Docker)

### Changed
- Configuration uses Pydantic models for validation
- Embeddings default to local ChromaDB (no API key required)
- Publishing moved from GCP Artifact Registry to PyPI

### Removed
- GCP Artifact Registry deployment (replaced with PyPI)
- Outdated DEPLOYMENT.md and INSTALL.md files

## [0.7.0] - 2024-06-27

### Added
- High-performance Rust analyzer with 3-10x speed improvement
- Comprehensive test suite for Rust core functionality
- Module-level enrichment file generation
- Self-documenting capabilities using autodoc's own tools
- Support for exclude patterns in Rust analyzer
- Enhanced decorator and parameter type extraction

### Fixed
- Line number calculation in Rust parser
- Parameter type annotation extraction
- API endpoint detection for Flask/FastAPI decorators
- AttributeError in inline enrichment for parent_class

### Changed
- Improved function signature extraction
- Enhanced Python-Rust interoperability via PyO3

## [0.6.0] - 2024-06-26

### Added
- Inline documentation enrichment feature
- Module enrichment file generation
- Support for AI-powered code documentation
- Integration with GPT-4o-mini for cost-effective enrichment

## [0.5.0] - 2024-06-25

### Added
- LLM-powered code enrichment for detailed documentation
- Support for OpenAI, Anthropic, and Ollama providers
- Enrichment caching for performance
- Enhanced documentation generation with enriched descriptions

## [0.4.0] - 2024-06-24

### Added
- TypeScript support with tree-sitter parser
- Graph visualization capabilities
- Neo4j integration for relationship analysis
- API server for REST access
- Local graph visualization without Neo4j

## [0.3.1] - 2024-06-23

### Fixed
- Cache loading compatibility issues
- Serialization of numpy arrays

## [0.3.0] - 2024-06-22

### Added
- ChromaDB integration for vector embeddings
- Semantic search capabilities
- Configuration file support (.autodoc.yml)
- Export/import functionality for team collaboration

## [0.2.0] - 2024-06-20

### Added
- AST analysis for Python files
- Basic CLI interface
- Caching system for analysis results
- Rich terminal output

## [0.1.0] - 2024-06-18

### Added
- Initial project structure
- Basic Python AST parsing
- Simple code entity extraction

---

*Developed with Claude (Anthropic) - Showcasing the future of AI-assisted development*
EOF < /dev/null