#!/bin/bash
# Autodoc Deployment Script
# Usage: ./scripts/deploy.sh [version_type]
# version_type: patch|minor|major (default: patch)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VERSION_TYPE=${1:-patch}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}Autodoc Deployment Script${NC}"
echo "========================="
echo ""

cd "$PROJECT_ROOT"

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Check GCP configuration
echo -e "${YELLOW}Checking GCP configuration...${NC}"
if ! make check-config > /dev/null 2>&1; then
    echo -e "${RED}Error: GCP configuration check failed${NC}"
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(hatch version)
echo "Current version: $CURRENT_VERSION"

# Bump version
echo -e "${YELLOW}Bumping version ($VERSION_TYPE)...${NC}"
hatch version "$VERSION_TYPE"
NEW_VERSION=$(hatch version)
echo -e "${GREEN}New version: $NEW_VERSION${NC}"

# Run tests and build
echo -e "${YELLOW}Running tests and building package...${NC}"
if ! make build; then
    echo -e "${RED}Build failed, reverting version${NC}"
    git checkout pyproject.toml
    exit 1
fi

# Commit version bump
echo -e "${YELLOW}Committing version bump...${NC}"
git add pyproject.toml
git commit -m "bump version to $NEW_VERSION"

# Create tag
echo -e "${YELLOW}Creating git tag...${NC}"
git tag "v$NEW_VERSION"

# Publish package
echo -e "${YELLOW}Publishing to GCP Artifact Registry...${NC}"
if ! make publish; then
    echo -e "${RED}Publish failed${NC}"
    echo "Tag and commit have been created but package not published"
    echo "You may need to push manually and retry publishing"
    exit 1
fi

# Push to git
echo -e "${YELLOW}Pushing to git...${NC}"
git push origin main
git push origin "v$NEW_VERSION"

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "========================="
echo "Version: $NEW_VERSION"
echo "Git tag: v$NEW_VERSION"
echo "Package published to GCP Artifact Registry"
echo ""
echo -e "${YELLOW}Install with:${NC}"
echo "pip install --index-url https://$(make info | grep 'Registry URL' | cut -d' ' -f3)/simple/ autodoc"