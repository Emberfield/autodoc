# Autodoc Package Management Makefile (uv-based)
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
	@echo "$(GREEN)Autodoc Package Management (uv-powered)$(NC)"
	@echo "======================================="
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@grep -E '^(setup|analyze|search|dev-install):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Testing Commands:$(NC)"
	@grep -E '^(test|test-unit|test-integration|test-coverage|lint|format):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Build & Publish Commands:$(NC)"
	@grep -E '^(clean|build|publish|release|quick-publish):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)GCP Setup Commands:$(NC)"
	@grep -E '^(setup-gcp|configure-auth|check-config|check-published):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(NC)"
	@grep -E '^(version|info):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial development environment setup with uv
	@echo "$(YELLOW)Setting up development environment with uv...$(NC)"
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "$(RED)Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)"; \
		exit 1; \
	fi
	uv sync --dev
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Activate with: source .venv/bin/activate$(NC)"

setup-graph: ## Setup with graph dependencies
	@echo "$(YELLOW)Setting up with graph dependencies...$(NC)"
	uv sync --dev --extra graph
	@echo "$(GREEN)✓ Development environment with graph features ready$(NC)"

analyze: ## Analyze current directory and save cache
	@echo "$(YELLOW)Analyzing codebase...$(NC)"
	uv run python -m autodoc.cli analyze . --save
	@echo "$(GREEN)✓ Analysis complete$(NC)"

search: ## Search code (usage: make search QUERY="your query")
	@if [ -z "$(QUERY)" ]; then \
		echo "$(RED)Error: Please provide a query. Usage: make search QUERY='your search term'$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Searching for: $(QUERY)$(NC)"
	uv run python -m autodoc.cli search "$(QUERY)"

generate-docs: ## Generate comprehensive documentation
	@echo "$(YELLOW)Generating documentation...$(NC)"
	uv run python -m autodoc.cli generate-summary --format markdown --output docs.md
	@echo "$(GREEN)✓ Documentation generated$(NC)"

# Graph commands (require graph dependencies)
build-graph: ## Build code relationship graph in Neo4j
	@echo "$(YELLOW)Building code graph...$(NC)"
	uv run python -m autodoc.cli build-graph --clear
	@echo "$(GREEN)✓ Graph built$(NC)"

visualize-graph: ## Create graph visualizations
	@echo "$(YELLOW)Creating graph visualizations...$(NC)"
	uv run python -m autodoc.cli visualize-graph --all
	@echo "$(GREEN)✓ Visualizations created$(NC)"

query-graph: ## Query the code graph for insights
	@echo "$(YELLOW)Querying code graph...$(NC)"
	uv run python -m autodoc.cli query-graph --all

# Local graph commands (work without Neo4j)
local-graph: ## Create local code visualizations (no Neo4j required)
	@echo "$(YELLOW)Creating local code graphs...$(NC)"
	uv run python -m autodoc.cli local-graph --all
	@echo "$(GREEN)✓ Local graphs created$(NC)"

local-stats: ## Show module statistics
	@echo "$(YELLOW)Generating module statistics...$(NC)"
	uv run python -m autodoc.cli local-graph --stats

test: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	uv run pytest tests/ -v
	@echo "$(GREEN)✓ Tests completed$(NC)"

test-core: ## Run core tests (excluding graph tests)
	@echo "$(YELLOW)Running core tests...$(NC)"
	uv run pytest tests/unit/ -v
	@echo "$(GREEN)✓ Core tests completed$(NC)"

test-graph: ## Run graph tests (requires graph dependencies)
	@echo "$(YELLOW)Running graph tests...$(NC)"
	uv run pytest tests/test_graph.py -v
	@echo "$(GREEN)✓ Graph tests completed$(NC)"

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	uv run pytest --cov=src/autodoc --cov-report=html --cov-report=term tests/
	@echo "$(GREEN)✓ Coverage report generated$(NC)"

demo-collab: ## Run the collaborative editing UI demo
	@echo "$(YELLOW)Running collaborative editing demo...$(NC)"
	uv run python demo_collaboration.py

# ========================================
# Rust Core Targets
# ========================================

build-rust: ## Build the high-performance Rust core
	@echo "$(YELLOW)Building Rust core...$(NC)"
	@cd rust-core && source "$$HOME/.cargo/env" && uv run maturin develop --release

install-rust: build-rust ## Build and install Rust core
	@echo "$(YELLOW)Installing Rust core...$(NC)"
	@pip install dist/autodoc_core-*.whl
	@echo "$(GREEN)✓ Rust core installed$(NC)"

test-rust: ## Test Rust core
	@echo "$(YELLOW)Testing Rust core...$(NC)"
	@cd rust-core && cargo test
	@echo "$(GREEN)✓ Rust tests completed$(NC)"

benchmark: ## Run performance benchmark (Python vs Rust)
	@echo "$(YELLOW)Running performance benchmark...$(NC)"
	@uv run python -m autodoc.rust_analyzer
	@echo "$(GREEN)✓ Benchmark completed$(NC)"

clean-rust: ## Clean Rust build artifacts
	@echo "$(YELLOW)Cleaning Rust artifacts...$(NC)"
	@cd rust-core && cargo clean
	@rm -rf rust-core/target
	@echo "$(GREEN)✓ Rust artifacts cleaned$(NC)"".

dev-rust: ## Development mode with Rust core
	@echo "$(YELLOW)Setting up development with Rust core...$(NC)"
	@cd rust-core && maturin develop
	@echo "$(GREEN)✓ Rust core available in development mode$(NC)"".

check-rust: ## Check if Rust is installed
	@echo "$(YELLOW)Checking Rust installation...$(NC)"
	@if command -v rustc >/dev/null 2>&1; then \
		echo "$(GREEN)✅ Rust is installed: $$(rustc --version)$(NC)"; \
		echo "$(GREEN)✅ Cargo is installed: $$(cargo --version)$(NC)"; \
	else \
		echo "$(RED)❌ Rust is not installed$(NC)"; \
		echo "$(YELLOW)Install Rust from: https://rustup.rs$(NC)"; \
	fi

lint: ## Run code linting
	@echo "$(YELLOW)Running linter...$(NC)"
	uv run ruff check . || (echo "$(RED)Linting failed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Linting passed$(NC)"

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	uv run black .
	uv run ruff check . --fix
	@echo "$(GREEN)✓ Code formatted$(NC)"

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf $(DIST_DIR)/ $(BUILD_DIR)/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Clean complete$(NC)"

build: clean test ## Build the package
	@echo "$(YELLOW)Building package...$(NC)"
	uv build
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la $(DIST_DIR)/

dev-install: ## Install package in development mode
	@echo "$(YELLOW)Installing package in development mode...$(NC)"
	uv pip install -e .
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
	uv add --dev keyring keyrings.google-artifactregistry-auth twine
	gcloud auth configure-docker $(REGION)-docker.pkg.dev
	@echo "$(GREEN)✓ Authentication configured$(NC)"
	@echo ""
	@echo "$(YELLOW)Test authentication with:$(NC) gcloud artifacts print-settings python --repository=$(REPOSITORY) --location=$(REGION)"

publish: check-config build ## Publish package to GCP Artifact Registry
	@echo "$(YELLOW)Publishing to GCP Artifact Registry...$(NC)"
	@echo "Repository URL: $(REGISTRY_URL)/"
	@# Ensure we have the keyrings auth
	@uv pip install --quiet keyrings.google-artifactregistry-auth
	@# Configure twine to use the repository
	@mkdir -p ~/.config/pip
	@echo "[global]" > ~/.config/pip/pip.conf
	@echo "extra-index-url = $(REGISTRY_URL)/simple/" >> ~/.config/pip/pip.conf
	@# Upload using twine with keyring authentication
	uv run python -m twine upload \
		--repository-url $(REGISTRY_URL)/ \
		$(DIST_DIR)/*
	@echo "$(GREEN)✓ Package published successfully$(NC)"
	@echo ""
	@echo "$(YELLOW)Install with:$(NC) pip install --index-url $(REGISTRY_URL)/simple/ $(PACKAGE_NAME)"

check-published: check-config ## Check published packages in Artifact Registry
	@echo "$(YELLOW)Checking published packages...$(NC)"
	gcloud artifacts packages list --repository=$(REPOSITORY) --location=$(REGION)

release: ## Create a new release (interactive version bump)
	@echo "$(YELLOW)Creating new release...$(NC)"
	@echo "Current version: $$(uv run python -c 'from src.autodoc.__about__ import __version__; print(__version__)')"
	@echo ""
	@echo "Select version bump:"
	@echo "1) patch (x.y.z -> x.y.z+1)"
	@echo "2) minor (x.y.z -> x.y+1.0)"
	@echo "3) major (x.y.z -> x+1.0.0)"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) python scripts/bump_version.py patch ;; \
		2) python scripts/bump_version.py minor ;; \
		3) python scripts/bump_version.py major ;; \
		*) echo "$(RED)Invalid choice$(NC)"; exit 1 ;; \
	esac
	@echo "$(GREEN)Version updated$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. Commit changes: git add . && git commit -m 'bump version'"
	@echo "2. Create tag: git tag v$$(uv run python -c 'from src.autodoc.__about__ import __version__; print(__version__)')"
	@echo "3. Push: git push && git push --tags"
	@echo "4. Publish: make publish"

version: ## Show current version
	@uv run python -c "from src.autodoc.__about__ import __version__; print(f'Current version: {__version__}')"

info: ## Show project information
	@echo "$(GREEN)Autodoc Package Information$(NC)"
	@echo "=========================="
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Version: $$(uv run python -c 'from src.autodoc.__about__ import __version__; print(__version__)' 2>/dev/null || echo 'Unknown')"
	@echo "Project: $(PROJECT_ID)"
	@echo "Region: $(REGION)"
	@echo "Repository: $(REPOSITORY)"
	@echo "Registry URL: $(REGISTRY_URL)"
	@echo ""
	@echo "$(YELLOW)Dependencies:$(NC)"
	@echo "uv: $$(uv --version 2>/dev/null || echo 'Not installed')"
	@echo "Python: $$(python --version 2>/dev/null || echo 'Not found')"

check: ## Check environment and dependencies
	@echo "$(YELLOW)Checking environment...$(NC)"
	uv run python -m autodoc.cli check
	@echo "$(GREEN)✓ Environment check complete$(NC)"

# Convenience commands
quick-publish: format lint test build publish ## Quick publish workflow (format, lint, test, build, publish)
	@echo "$(GREEN)✓ Quick publish complete$(NC)"

full-setup: setup setup-gcp configure-auth ## Complete setup for new development environment
	@echo "$(GREEN)✓ Full setup complete - ready for development!$(NC)"

# Development workflow commands
dev: setup analyze ## Quick development setup
	@echo "$(GREEN)✓ Development environment ready. Run 'source .venv/bin/activate' to activate.$(NC)"

dev-graph: setup-graph analyze build-graph ## Development setup with graph features
	@echo "$(GREEN)✓ Development environment with graph features ready!$(NC)"