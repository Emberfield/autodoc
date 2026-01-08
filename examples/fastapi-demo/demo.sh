#!/bin/bash
# Autodoc Demo Script - Analyze FastAPI
# This script demonstrates autodoc's full feature set on a real codebase
#
# Usage: ./demo.sh [--quick]
#   --quick  Use pre-computed data for instant results (no API keys needed)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Parse arguments
QUICK_MODE=false
if [ "$1" = "--quick" ]; then
    QUICK_MODE=true
fi

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTODOC_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
REPO_DIR="$DEMO_DIR/fastapi-repo"
PRECOMPUTED_DIR="$DEMO_DIR/precomputed"

# Helper function to run autodoc commands
# Runs from REPO_DIR to ensure cache files are saved there
autodoc_run() {
    cd "$REPO_DIR" && PYTHONPATH="$AUTODOC_ROOT/src" "$AUTODOC_ROOT/.venv/bin/python" -m autodoc.cli "$@"
}

# Step 1: Clone FastAPI (if not exists)
print_step "Step 1: Setting up FastAPI repository"
if [ -d "$REPO_DIR" ]; then
    print_info "FastAPI repo already exists, skipping clone..."
else
    print_info "Cloning FastAPI (shallow clone for speed)..."
    git clone --depth 1 https://github.com/tiangolo/fastapi.git "$REPO_DIR"
fi

# Quick mode: use pre-computed data
if [ "$QUICK_MODE" = true ]; then
    print_step "Quick Mode: Using pre-computed analysis data"
    if [ -d "$PRECOMPUTED_DIR" ]; then
        print_info "Copying pre-computed analysis, packs, and enrichment data..."
        cp "$PRECOMPUTED_DIR/autodoc_cache.json" "$REPO_DIR/"
        cp "$PRECOMPUTED_DIR/.autodoc.yaml" "$REPO_DIR/"
        cp "$PRECOMPUTED_DIR/autodoc_enrichment_cache.json" "$REPO_DIR/"
        print_info "Pre-computed data loaded! (370 entities, 2 packs, 15 enriched)"
    else
        print_info "Pre-computed data not found, running full analysis..."
        QUICK_MODE=false
    fi
fi

if [ "$QUICK_MODE" = false ]; then
    # Step 2: Analyze the codebase
    print_step "Step 2: Analyzing codebase structure"
    print_info "This extracts all functions, classes, and their relationships..."
    autodoc_run analyze ./fastapi --save

    # Step 3: Check what we found
    print_step "Step 3: Checking analysis results"
    autodoc_run check

    # Step 4: Auto-generate context packs
    print_step "Step 4: Auto-generating context packs"
    print_info "Autodoc detects logical groupings based on directory structure..."
    autodoc_run pack auto-generate --save
fi

# Step 5: List the packs
print_step "Step 5: Listing detected packs"
autodoc_run pack list

# Step 6: Search for code
print_step "Step 6: Semantic search examples"
print_info "Searching for 'dependency injection'..."
autodoc_run search "dependency injection" --limit 5 || print_info "Search returned no results"

echo ""
print_info "Searching for 'request validation'..."
autodoc_run search "request validation" --limit 5 || print_info "Search returned no results"

# Step 7: Enrich with AI (if API key available or pre-computed)
print_step "Step 7: AI-powered enrichment"
if [ -f "$REPO_DIR/autodoc_enrichment_cache.json" ] && [ "$(wc -c < "$REPO_DIR/autodoc_enrichment_cache.json")" -gt 10 ]; then
    print_info "Enrichment data available! (15 key FastAPI entities documented)"
    print_info "Sample enrichments include: Path, Query, Header, FastAPI, APIRouter, OAuth2..."
elif [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
    print_info "API key found! Running enrichment on a sample..."
    autodoc_run enrich --inline --limit 10 --no-backup || print_info "Enrichment skipped"
else
    print_info "No API key found. Using pre-computed enrichment data if available..."
    if [ -f "$PRECOMPUTED_DIR/autodoc_enrichment_cache.json" ]; then
        cp "$PRECOMPUTED_DIR/autodoc_enrichment_cache.json" "$REPO_DIR/"
        print_info "Pre-computed enrichments loaded! (15 key entities)"
    else
        print_info "Set ANTHROPIC_API_KEY or OPENAI_API_KEY to generate fresh enrichments."
    fi
fi

# Step 8: Feature detection (requires Neo4j)
print_step "Step 8: Feature detection (requires Neo4j + GDS)"
if [ -n "$NEO4J_URI" ] && [ -n "$NEO4J_PASSWORD" ]; then
    print_info "Neo4j configured. Building code graph..."
    autodoc_run graph --clear || print_info "Graph build skipped (Neo4j not reachable)"

    print_info "Detecting features..."
    autodoc_run features detect || print_info "Feature detection skipped"
else
    print_info "Neo4j not configured. Set NEO4J_URI and NEO4J_PASSWORD for feature detection."
    print_info "Feature detection uses graph analysis to find code clusters automatically."
    print_info "Skipping graph and feature detection..."
fi

# Summary
print_step "Demo Complete!"
echo -e "
${GREEN}What we demonstrated:${NC}
  ✓ Codebase analysis (AST parsing)
  ✓ Context pack auto-generation
  ✓ Semantic code search
  ✓ AI enrichment (pre-computed sample data)
  ✗ Feature detection (requires Neo4j)

${YELLOW}Next steps:${NC}
  • Run 'autodoc pack query tests \"test coverage\"' for pack-specific search
  • Run 'autodoc pack build --all --embeddings' for vector embeddings
  • Run 'autodoc mcp-server' to integrate with AI assistants
  • Check .autodoc.yaml for configuration options

${BLUE}Learn more: https://autodoc.tools${NC}
"

# Step 9: Launch Dashboard
print_step "Step 9: Launching Dashboard UI"
DASHBOARD_DIR="$AUTODOC_ROOT/dashboard"

if [ -d "$DASHBOARD_DIR" ]; then
    print_info "Starting dashboard at http://localhost:3000"
    print_info "Press Ctrl+C to stop the dashboard"
    echo ""

    # Check if npm dependencies are installed
    if [ ! -d "$DASHBOARD_DIR/node_modules" ]; then
        print_info "Installing dashboard dependencies..."
        cd "$DASHBOARD_DIR" && npm install
    fi

    # Set working directory for dashboard to read demo data
    export AUTODOC_PROJECT_ROOT="$REPO_DIR"

    # Open browser (works on macOS, Linux with xdg-open, or Windows with start)
    sleep 2 && (open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || start http://localhost:3000 2>/dev/null) &

    # Start the dashboard
    cd "$DASHBOARD_DIR" && npm run dev
else
    print_info "Dashboard not found at $DASHBOARD_DIR"
    print_info "Run 'make dashboard' from the autodoc root directory"
fi
