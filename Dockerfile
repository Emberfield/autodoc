# Autodoc MCP Server
# Lightweight container for Cloud Run deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy all files needed for installation
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install the package (non-editable for production)
RUN uv pip install --system --no-cache .

# Create non-root user for security
RUN useradd -m -u 1000 autodoc
USER autodoc

# Cloud Run uses PORT env var
ENV PORT=8080
ENV HOST=0.0.0.0

# Run the MCP server with SSE transport
CMD ["python", "-m", "autodoc.mcp_server", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
