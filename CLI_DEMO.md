# Autodoc CLI Commands Reference

After installing the Autodoc package, users will have access to the `autodoc` command with the following capabilities:

## Core Commands

### `autodoc --help`
Shows all available commands:
```
Usage: autodoc [OPTIONS] COMMAND [ARGS]...

  Autodoc - AI-powered code intelligence

Options:
  --help  Show this message and exit.

Commands:
  analyze           Analyze a codebase
  build-graph       Build code relationship graph in Neo4j
  check             Check dependencies and configuration
  generate-summary  Generate a comprehensive codebase summary optimized...
  local-graph       Create code visualizations without Neo4j (uses local...
  query-graph       Query the code graph for insights
  search            Search for code
  visualize-graph   Create interactive visualizations of the code graph
```

### `autodoc check`
Verify environment and configuration:
```bash
autodoc check
# Output:
# Autodoc Status:
# 
# ❌ OpenAI API key not found
#    Set OPENAI_API_KEY in .env file
# ℹ️  No analyzed code found - run 'autodoc analyze' first
```

### `autodoc analyze [PATH] [--save]`
Analyze a codebase and extract code entities:
```bash
# Analyze current directory
autodoc analyze . --save

# Analyze specific path
autodoc analyze /path/to/project --save

# Options:
#   --save  Save analysis to cache for later use
```

### `autodoc search "query" [--limit N]`
Search analyzed code using natural language:
```bash
# Search for authentication-related code
autodoc search "authentication" --limit 5

# Search for specific patterns
autodoc search "async function" --limit 10

# Options:
#   --limit INTEGER  Number of results (default: 5)
```

### `autodoc generate-summary [--output FILE] [--format FORMAT]`
Generate comprehensive codebase documentation:
```bash
# Generate markdown summary
autodoc generate-summary --format markdown --output docs.md

# Generate JSON data
autodoc generate-summary --format json --output data.json

# Output to console
autodoc generate-summary

# Options:
#   -o, --output TEXT         Save summary to file
#   --format [markdown|json]  Output format (default: markdown)
```

## Visualization Commands

### `autodoc local-graph [OPTIONS]`
Create code visualizations without requiring Neo4j:
```bash
# Create all visualizations
autodoc local-graph --all

# Create specific visualizations
autodoc local-graph --files      # File dependency graph
autodoc local-graph --entities   # Entity network graph
autodoc local-graph --stats      # Module statistics

# Options:
#   --files     Create file dependency graph
#   --entities  Create entity network graph
#   --stats     Show module statistics
#   --all       Create all visualizations
```

## Advanced Graph Commands (Optional Dependencies)

### `autodoc build-graph [--clear]`
Build code relationship graph in Neo4j:
```bash
autodoc build-graph --clear

# Options:
#   --clear  Clear existing graph data
```

### `autodoc visualize-graph [OPTIONS]`
Create interactive visualizations from Neo4j graph:
```bash
autodoc visualize-graph --all

# Options:
#   -o, --output TEXT  Output file for interactive graph
#   --deps            Create module dependency graph
#   --complexity      Create complexity heatmap
#   --all             Create all visualizations
```

### `autodoc query-graph [OPTIONS]`
Query the Neo4j graph for insights:
```bash
autodoc query-graph --all

# Options:
#   --entry-points   Find entry points
#   --test-coverage  Analyze test coverage
#   --patterns       Find code patterns
#   --complexity     Show module complexity
#   --deps TEXT      Find dependencies for entity
#   --all            Show all analysis
```

## Example Workflows

### Basic Workflow
```bash
# 1. Check status
autodoc check

# 2. Analyze codebase
autodoc analyze . --save

# 3. Search for specific functionality
autodoc search "error handling" --limit 5

# 4. Generate documentation
autodoc generate-summary --format markdown --output codebase-docs.md
```

### With Visualizations
```bash
# 1. Analyze codebase
autodoc analyze . --save

# 2. Create local visualizations (no external dependencies)
autodoc local-graph --all

# 3. Generate comprehensive docs
autodoc generate-summary --output comprehensive-docs.md
```

### Advanced Graph Analysis (requires Neo4j + graph dependencies)
```bash
# 1. Analyze codebase
autodoc analyze . --save

# 2. Build graph database
autodoc build-graph --clear

# 3. Create interactive visualizations
autodoc visualize-graph --all

# 4. Query for insights
autodoc query-graph --all
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - For enhanced semantic search (optional)

### Files Created
- `autodoc_cache.json` - Analysis cache (when using --save)
- `*.html` - Interactive visualization files
- `*.png` - Static graph images
- `*.md` - Generated documentation

## Error Handling

Commands gracefully handle:
- Missing dependencies (graph features)
- No OpenAI API key (falls back to text search)
- Invalid file paths
- Empty or broken Python files
- Missing analysis cache

## Integration

The CLI can be integrated into:
- Development workflows
- CI/CD pipelines
- Documentation generation
- Code review processes
- Team onboarding

All commands provide helpful error messages and suggestions for next steps.