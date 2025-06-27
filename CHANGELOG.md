# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2024-01-26

### Added
- 📝 **Inline Documentation** - Revolutionary inline docstring enrichment
  - Add enriched docstrings directly to your code files with `--inline`
  - Smart docstring placement with proper indentation
  - Preserves existing good docstrings, only improves basic ones
  - Optional backup files for safety (`--backup/--no-backup`)
  - Incremental processing - only updates changed files

- 📁 **Module-Level Enrichment Files** - Comprehensive module documentation
  - Generate `.enrichment.md` or `.enrichment.json` files with `--module-files`
  - Complete module overview with entity summaries
  - Enriched descriptions, key features, usage examples
  - Perfect for code reviews and onboarding

- 🔄 **Change Detection** - Smart incremental enrichment
  - Tracks file modifications, content hashes, and entity counts
  - Only processes files that have actually changed
  - Persistent cache in `.autodoc_file_changes.json`
  - Significant performance improvement for large codebases

- ✨ **Enhanced CLI Commands**
  - `autodoc enrich --inline` - Add docstrings directly to code
  - `autodoc enrich --module-files` - Generate module enrichment files
  - `autodoc generate --enrich --inline` - One-command enrichment + docs
  - Flexible options: `--incremental`, `--backup`, `--module-format`

### Improved
- 🔧 **Smarter Enrichment Logic**
  - Works with cached enrichments even without API keys
  - Better error handling for missing dependencies
  - More informative progress messages
  - Robust AST parsing and docstring detection

- 🚀 **Developer Experience**
  - Enrichments now live in your actual code files
  - Perfect for IDE integration and code completion
  - Module files provide comprehensive documentation
  - Incremental updates keep enrichments fresh

### Technical
- Comprehensive AST-based docstring manipulation
- File change detection with content hashing
- Modular enrichment architecture
- Extensive test coverage (95 tests passing)

## [0.4.0] - 2024-01-26

### Added
- 🚀 **ChromaDB Support** - Local embeddings without API requirements
  - Use ChromaDB as an alternative to OpenAI embeddings
  - Local sentence transformers for privacy and cost savings
  - Persistent storage with SQLite backend
  - Configure via `embeddings.provider: chromadb` in config

- 🔄 **Embedding Regeneration** - Keep embeddings fresh with enriched content
  - Added `--regenerate-embeddings` flag to `autodoc enrich`
  - Automatically uses enriched descriptions for better search
  - Works with both OpenAI and ChromaDB providers

- 🎯 **Enhanced Search** - Improved semantic search with provider flexibility
  - ChromaDB search with similarity scoring
  - Metadata filtering for targeted results
  - Seamless provider switching via config

### Improved
- 📊 **Better Status Checking**
  - `autodoc check` now shows embedding provider status
  - ChromaDB stats including model and embedding count
  - Configuration file detection

- 🔧 **Smarter Vector Command**
  - Detects and uses configured embedding provider
  - Shows enrichment ratio for ChromaDB
  - Clearer messaging for provider requirements

## [0.3.1] - 2024-01-26

### Fixed
- 🐛 **Cache Loading Compatibility** - Critical fix for loading cached entities
  - Fixed TypeError when loading cache files with extra fields (like `is_async`)
  - Made cache loading more robust by filtering to valid CodeEntity fields
  - Added comprehensive tests to prevent future compatibility issues
  - This fixes the "unexpected keyword argument 'is_async'" error

## [0.3.0] - 2024-01-26

### Added
- 🤖 **LLM-Powered Code Enrichment** - Revolutionary feature for AI-enhanced documentation
  - Support for OpenAI, Anthropic/Claude, and Ollama
  - Generates detailed descriptions of code functionality
  - Identifies key features, complexity, and design patterns
  - Creates usage examples automatically
  - Caches results for efficient processing

- 🔧 **Configuration System** - Flexible settings management
  - New `.autodoc.yml` configuration file
  - `autodoc init` command to create config
  - Support for multiple LLM providers
  - Customizable enrichment settings

- 📝 **Enhanced Build Documentation** - Complete build system information
  - Comprehensive Makefile parser
  - Extracts all targets with descriptions
  - Categorizes commands (setup, build, test, lint, etc.)
  - Shows command parameters and usage

- 🎯 **New CLI Commands**
  - `autodoc init` - Initialize configuration
  - `autodoc enrich` - Enrich code with LLM analysis
  - Made `--detailed` the default for `autodoc generate`

### Improved
- 📊 **Better Documentation Quality**
  - Enriched descriptions in generated docs
  - Enhanced embeddings using enriched content
  - More meaningful semantic search results
  - Detailed build/test/publish commands

- 🐛 **GitHub Workflow Fix**
  - Fixed Claude Code action configuration
  - Added required OIDC token permissions

## [0.2.1] - 2024-01-26

### Fixed
- 🐛 **Graph Error Messages** - Improved error handling and dependency detection
  - Shows which specific graph dependencies are missing
  - Distinguishes between missing deps vs Neo4j not running
  - Added helpful guidance for starting Neo4j or using local-graph alternative
  - Fixed incomplete dependency lists in error messages (added networkx, pyvis)

### Improved
- 📝 **Makefile Publishing** - Fixed authentication for GCP Artifact Registry
  - Use keyrings.google-artifactregistry-auth instead of oauth2accesstoken
  - Fixed pip command to use `uv pip` for consistency

## [0.2.0] - 2024-01-26

### Added
- 🚀 **Full TypeScript Support**
  - Complete TypeScript AST analysis using tree-sitter
  - Smart fallback to regex parser when tree-sitter unavailable  
  - Framework detection (Express, NestJS, React, Angular, Vue)
  - Internal/external service classification
  - Mixed Python/TypeScript project support
  - Language-specific statistics and reporting

- 🎯 **Simplified CLI Commands**
  - `autodoc generate` - Creates AUTODOC.md with zero config
  - `autodoc graph` - Builds graph database (was build-graph)
  - `autodoc vector` - NEW: Generate embeddings for semantic search
  - Built-in quick start guide in --help
  - Smart file extension handling

- 🌐 **API Server** (`autodoc serve`)
  - REST API for code analysis
  - Internal vs external node classification
  - CORS support for web integration
  - Relationship mapping endpoints

- 🧪 **Testing Improvements**
  - 100% test success rate (70 tests passing)
  - Comprehensive TypeScript test suite
  - Graph test mocking framework
  - Modular test organization

### Changed
- Simplified CLI with intuitive commands and sensible defaults
- Enhanced graph database integration with proper mocking
- Improved error messages and user guidance
- Better language statistics calculation

### Fixed
- Language statistics calculation bug (list reference issue)
- Graph connection error handling
- Test import paths for better compatibility
- Mock context manager setup for database tests

### Technical
- Migrated to `uv` package manager
- Enhanced CI/CD with GitHub Actions
- Improved package structure and imports
- Better TypeScript entity classification logic

## [0.1.0] - 2024-01-20

### Added
- Initial release with Python code analysis
- AST-based code entity extraction
- OpenAI embeddings integration
- Neo4j graph database support
- Basic CLI interface
- Search functionality