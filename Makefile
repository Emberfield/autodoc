# Autodoc Package Management Makefile
# Usage: make <target>

# Variables - override these as needed
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
REGION ?= us-central1
REPOSITORY ?= autodoc-repo
PACKAGE_NAME ?= autodoc

# Derived variables
REGISTRY_URL = https://$(REGION)-python.pkg.dev/$(PROJECT_ID)/$(REPOSITORY)
DIST_DIR = dist
BUILD_DIR = build

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

.PHONY: help setup analyze search test build clean publish dev-install lint format
.PHONY: check-config setup-gcp configure-auth check-published release version info

help: ## Show this help message
	@echo "$(GREEN)Autodoc Package Management$(NC)"
	@echo "=========================="
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@grep -E '^(setup|analyze|search|test|lint|format|dev-install):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Build & Publish Commands:$(NC)"
	@grep -E '^(clean|build|publish|release|quick-publish):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)GCP Setup Commands:$(NC)"
	@grep -E '^(setup-gcp|configure-auth|check-config|check-published):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(NC)"
	@grep -E '^(version|info):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial development environment setup
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	hatch env create
	@echo "$(GREEN)✓ Development environment ready$(NC)"

analyze: ## Analyze current directory and save cache
	@echo "$(YELLOW)Analyzing codebase...$(NC)"
	hatch run analyze . --save
	@echo "$(GREEN)✓ Analysis complete$(NC)"

search: ## Search code (usage: make search QUERY="your query")
	@if [ -z "$(QUERY)" ]; then \
		echo "$(RED)Error: Please provide a query. Usage: make search QUERY='your search term'$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Searching for: $(QUERY)$(NC)"
	hatch run search "$(QUERY)"

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	hatch run test
	@echo "$(GREEN)✓ Tests completed$(NC)"

lint: ## Run code linting
	@echo "$(YELLOW)Running linter...$(NC)"
	hatch run ruff check . || (echo "$(RED)Linting failed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Linting passed$(NC)"

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	hatch run black .
	hatch run ruff check . --fix
	@echo "$(GREEN)✓ Code formatted$(NC)"

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf $(DIST_DIR)/ $(BUILD_DIR)/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Clean complete$(NC)"

build: clean test ## Build the package
	@echo "$(YELLOW)Building package...$(NC)"
	hatch build
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la $(DIST_DIR)/

dev-install: ## Install package in development mode
	@echo "$(YELLOW)Installing package in development mode...$(NC)"
	pip install -e .
	@echo "$(GREEN)✓ Development installation complete$(NC)"

# GCP Artifact Registry Commands

check-config: ## Check GCP configuration
	@echo "$(YELLOW)Checking GCP configuration...$(NC)"
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "$(RED)Error: GCP project not set. Run 'gcloud config set project YOUR_PROJECT_ID'$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Project ID: $(PROJECT_ID)$(NC)"
	@echo "$(GREEN)✓ Region: $(REGION)$(NC)"
	@echo "$(GREEN)✓ Repository: $(REPOSITORY)$(NC)"
	@echo "$(GREEN)✓ Registry URL: $(REGISTRY_URL)$(NC)"

setup-gcp: check-config ## Setup GCP Artifact Registry repository
	@echo "$(YELLOW)Setting up GCP Artifact Registry...$(NC)"
	@echo "Enabling Artifact Registry API..."
	gcloud services enable artifactregistry.googleapis.com
	@echo "Creating repository..."
	gcloud artifacts repositories create $(REPOSITORY) \
		--repository-format=python \
		--location=$(REGION) \
		--description="Private Python packages for $(PACKAGE_NAME)" || \
		echo "$(YELLOW)Repository may already exist$(NC)"
	@echo "$(GREEN)✓ GCP setup complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. Run 'make configure-auth' to set up authentication"
	@echo "2. Run 'make build' to build the package"
	@echo "3. Run 'make publish' to publish to Artifact Registry"

configure-auth: check-config ## Configure authentication for Artifact Registry
	@echo "$(YELLOW)Configuring authentication...$(NC)"
	pip install --upgrade keyring keyrings.google-artifactregistry-auth twine
	gcloud auth configure-docker $(REGION)-docker.pkg.dev
	@echo "$(GREEN)✓ Authentication configured$(NC)"
	@echo ""
	@echo "$(YELLOW)Test authentication with:$(NC) gcloud artifacts print-settings python --repository=$(REPOSITORY) --location=$(REGION)"

publish: check-config build ## Publish package to GCP Artifact Registry
	@echo "$(YELLOW)Publishing to GCP Artifact Registry...$(NC)"
	@echo "Repository URL: $(REGISTRY_URL)/simple/"
	python -m twine upload \
		--repository-url $(REGISTRY_URL)/simple/ \
		--username _json_key_base64 \
		$(DIST_DIR)/*
	@echo "$(GREEN)✓ Package published successfully$(NC)"
	@echo ""
	@echo "$(YELLOW)Install with:$(NC) pip install --index-url $(REGISTRY_URL)/simple/ $(PACKAGE_NAME)"

check-published: check-config ## Check published packages in Artifact Registry
	@echo "$(YELLOW)Checking published packages...$(NC)"
	gcloud artifacts packages list --repository=$(REPOSITORY) --location=$(REGION)

release: ## Create a new release (interactive version bump)
	@echo "$(YELLOW)Creating new release...$(NC)"
	@echo "Current version: $$(hatch version)"
	@echo ""
	@echo "Select version bump:"
	@echo "1) patch (x.y.z -> x.y.z+1)"
	@echo "2) minor (x.y.z -> x.y+1.0)"
	@echo "3) major (x.y.z -> x+1.0.0)"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) hatch version patch ;; \
		2) hatch version minor ;; \
		3) hatch version major ;; \
		*) echo "$(RED)Invalid choice$(NC)"; exit 1 ;; \
	esac
	@echo "$(GREEN)Version updated to: $$(hatch version)$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. Commit changes: git add . && git commit -m 'bump version to $$(hatch version)'"
	@echo "2. Create tag: git tag v$$(hatch version)"
	@echo "3. Push: git push && git push --tags"
	@echo "4. Publish: make publish"

version: ## Show current version
	@echo "Current version: $$(hatch version)"

info: ## Show project information
	@echo "$(GREEN)Autodoc Package Information$(NC)"
	@echo "=========================="
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Version: $$(hatch version 2>/dev/null || echo 'Unknown')"
	@echo "Project: $(PROJECT_ID)"
	@echo "Region: $(REGION)"
	@echo "Repository: $(REPOSITORY)"
	@echo "Registry URL: $(REGISTRY_URL)"

# Convenience commands
quick-publish: format lint test build publish ## Quick publish workflow (format, lint, test, build, publish)
	@echo "$(GREEN)✓ Quick publish complete$(NC)"

full-setup: setup setup-gcp configure-auth ## Complete setup for new development environment
	@echo "$(GREEN)✓ Full setup complete - ready for development!$(NC)"
