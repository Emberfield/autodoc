# Autodoc Deployment Guide

## Quick Start

Your GCP Artifact Registry publishing is now set up! Here's how to deploy releases:

### 1. One-Time Setup

```bash
# Ensure gcloud is configured (already done)
gcloud config get-value project  # Should show: the-agent-factory

# Set up the GCP repository and authentication
make setup-gcp
make configure-auth
```

### 2. Deploy a Release

**Option A: Interactive Release (Recommended)**
```bash
make release     # Interactive version bump
make publish     # Publish to Artifact Registry
```

**Option B: Quick Publish**
```bash
make quick-publish  # Format, lint, test, build, and publish in one command
```

**Option C: Automated Script**
```bash
./scripts/deploy.sh patch   # or minor/major
```

## Available Make Commands

### Development
```bash
make setup          # Set up development environment
make test           # Run tests
make lint           # Check code quality
make format         # Format code
make analyze        # Analyze current codebase
make search QUERY="your search"  # Search code
```

### Build & Publish
```bash
make clean          # Clean build artifacts
make build          # Build package (runs tests first)
make publish        # Publish to GCP Artifact Registry
make release        # Interactive version bump
make quick-publish  # Full pipeline in one command
```

### GCP Management
```bash
make check-config      # Verify GCP settings
make setup-gcp         # Create Artifact Registry repository
make configure-auth    # Set up authentication
make check-published   # List published packages
```

### Utilities
```bash
make version        # Show current version
make info          # Show project information
make help          # Show all commands
```

## Repository Configuration

- **Project ID**: `the-agent-factory`
- **Region**: `us-central1`
- **Repository**: `autodoc-repo`
- **Registry URL**: `https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo`

## Team Installation

Team members can install the package with:

```bash
# Install keyring for authentication
pip install keyrings.google-artifactregistry-auth

# Authenticate with GCP
gcloud auth application-default login

# Install autodoc
pip install --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/ autodoc
```

See `INSTALL.md` for detailed installation instructions.

## GitHub Actions (Optional)

The `.github/workflows/publish.yml` file provides automated publishing on:
- GitHub releases (manual)
- Workflow dispatch (manual trigger)

To enable, you'll need to set up Workload Identity Federation:

1. Create a service account with Artifact Registry Writer permissions
2. Set up Workload Identity Federation
3. Add secrets to GitHub:
   - `WIF_PROVIDER`: Workload Identity Provider ID
   - `WIF_SERVICE_ACCOUNT`: Service account email

## Versioning Strategy

The project uses semantic versioning (MAJOR.MINOR.PATCH):

- **Patch** (0.1.0 → 0.1.1): Bug fixes, minor changes
- **Minor** (0.1.0 → 0.2.0): New features, backward compatible
- **Major** (0.1.0 → 1.0.0): Breaking changes

Use `make release` for interactive version selection.

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth application-default login

# Test access
gcloud artifacts repositories list --location=us-central1
```

### Build Issues
```bash
# Clean and rebuild
make clean
make build
```

### Publishing Issues
```bash
# Check configuration
make check-config

# Verify authentication
make configure-auth
```

## Next Steps

1. **First Deployment**: Run `make setup-gcp && make configure-auth`
2. **Test Build**: Run `make build` to ensure everything works
3. **First Release**: Run `make release` and `make publish`
4. **Share with Team**: Distribute `INSTALL.md` to team members

Your private package repository is ready! 🚀