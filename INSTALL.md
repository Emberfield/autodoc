# Autodoc Installation Guide

This guide explains how to install and use the private Autodoc package from GCP Artifact Registry.

## Prerequisites

- Python 3.8+
- Access to `the-agent-factory` GCP project
- `gcloud` CLI installed and configured

## Installation

### Option 1: Direct Installation (Recommended)

```bash
# Configure authentication
gcloud auth application-default login

# Install the keyring plugin for Artifact Registry
pip install keyrings.google-artifactregistry-auth

# Install autodoc
pip install --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/ autodoc
```

### Option 2: Using pip.conf (Persistent Configuration)

Create `~/.pip/pip.conf` (Linux/Mac) or `%APPDATA%\pip\pip.ini` (Windows):

```ini
[global]
index-url = https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/
trusted-host = us-central1-python.pkg.dev
```

Then install normally:
```bash
pip install autodoc
```

### Option 3: In requirements.txt

```txt
# requirements.txt
--index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/
autodoc>=0.1.0
```

## Environment Setup

If you're using OpenAI embeddings (optional):

```bash
# Create .env file in your project
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

## Usage

### Basic Usage

```bash
# Check installation
autodoc --help

# Analyze a codebase
autodoc analyze /path/to/code --save

# Search analyzed code
autodoc search "function that handles authentication"

# Generate comprehensive documentation
autodoc generate-summary --format markdown --output docs.md
```

### Python API

```python
from autodoc import SimpleAutodoc
import asyncio

async def main():
    autodoc = SimpleAutodoc()
    summary = await autodoc.analyze_directory("./src")
    print(f"Found {summary['total_entities']} code entities")

asyncio.run(main())
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:

```bash
# Re-authenticate with Google Cloud
gcloud auth application-default login

# Verify access to the repository
gcloud artifacts repositories list --location=us-central1

# Test authentication
pip install --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/ --dry-run autodoc
```

### Version Issues

```bash
# Check available versions
pip index versions autodoc --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/

# Install specific version
pip install autodoc==0.1.0 --index-url https://us-central1-python.pkg.dev/the-agent-factory/autodoc-repo/simple/
```

### Permission Issues

If you can't access the repository, contact your admin to:
1. Add you to the `the-agent-factory` GCP project
2. Grant you `Artifact Registry Reader` role
3. Ensure you have access to the `autodoc-repo` repository

## Development Installation

For development work:

```bash
# Clone the repository
git clone https://github.com/your-org/autodoc.git
cd autodoc

# Install in development mode
pip install -e .

# Or using the Makefile
make dev-install
```

## Support

- **Repository Issues**: [GitHub Issues](https://github.com/your-org/autodoc/issues)
- **GCP Access**: Contact your GCP administrator
- **Package Updates**: Check the `#autodoc` Slack channel for announcements