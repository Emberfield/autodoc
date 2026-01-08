#!/bin/bash
# Autodoc Demo Script - Analyze FastAPI
# This script demonstrates autodoc's full feature set on a real codebase

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

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$DEMO_DIR/fastapi-repo"

# Step 1: Clone FastAPI (if not exists)
print_step "Step 1: Setting up FastAPI repository"
if [ -d "$REPO_DIR" ]; then
    print_info "FastAPI repo already exists, skipping clone..."
else
    print_info "Cloning FastAPI (shallow clone for speed)..."
    git clone --depth 1 https://github.com/tiangolo/fastapi.git "$REPO_DIR"
fi

cd "$REPO_DIR"

# Step 2: Analyze the codebase
print_step "Step 2: Analyzing codebase structure"
print_info "This extracts all functions, classes, and their relationships..."
autodoc analyze ./fastapi --save

# Step 3: Check what we found
print_step "Step 3: Checking analysis results"
autodoc check

# Step 4: Auto-generate context packs
print_step "Step 4: Auto-generating context packs"
print_info "Autodoc detects logical groupings based on directory structure..."
autodoc pack auto-generate --save

# Step 5: List the packs
print_step "Step 5: Listing detected packs"
autodoc pack list

# Step 6: Search for code
print_step "Step 6: Semantic search examples"
print_info "Searching for 'dependency injection'..."
autodoc search "dependency injection" --limit 5

echo ""
print_info "Searching for 'request validation'..."
autodoc search "request validation" --limit 5

# Step 7: Enrich with AI (if API key available)
print_step "Step 7: AI-powered enrichment (optional)"
if [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
    print_info "API key found! Running enrichment on a sample..."
    autodoc enrich --inline --limit 10 --no-backup
else
    print_info "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable AI enrichment."
    print_info "Skipping enrichment step..."
fi

# Step 8: Feature detection (requires Neo4j)
print_step "Step 8: Feature detection (requires Neo4j + GDS)"
if command -v neo4j &> /dev/null || [ -n "$NEO4J_URI" ]; then
    print_info "Building code graph..."
    autodoc graph --clear || print_info "Graph build skipped (Neo4j not configured)"

    print_info "Detecting features..."
    autodoc features detect || print_info "Feature detection skipped"
else
    print_info "Neo4j not found. Install Neo4j with GDS plugin for feature detection."
    print_info "Skipping graph and feature detection..."
fi

# Summary
print_step "Demo Complete!"
echo -e "
${GREEN}What we demonstrated:${NC}
  ✓ Codebase analysis (AST parsing)
  ✓ Context pack auto-generation
  ✓ Semantic code search
  ✓ AI enrichment (if API key provided)
  ✓ Feature detection (if Neo4j available)

${YELLOW}Next steps:${NC}
  • Run 'autodoc pack query routing \"how does routing work\"' for pack-specific search
  • Run 'autodoc pack build --all --embeddings' for vector embeddings
  • Run 'autodoc mcp-server' to integrate with AI assistants
  • Check .autodoc.yaml for configuration options

${BLUE}Learn more: https://autodoc.tools${NC}
"

# Step 9: Launch Dashboard
print_step "Step 9: Launching Dashboard UI"
AUTODOC_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
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

    # Open browser (works on macOS, Linux with xdg-open, or Windows with start)
    sleep 2 && (open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || start http://localhost:3000 2>/dev/null) &

    # Start the dashboard
    cd "$DASHBOARD_DIR" && npm run dev
else
    print_info "Dashboard not found at $DASHBOARD_DIR"
    print_info "Run 'make dashboard' from the autodoc root directory"
fi
