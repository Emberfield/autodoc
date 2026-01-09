# Autodoc Cloud API - Cloud Run Container

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install autodoc from PyPI (for analysis)
# Note: In production, pin to specific version
RUN pip install --no-cache-dir autodoc-ai || pip install --no-cache-dir git+https://github.com/autodoc-ai/autodoc.git || echo "Autodoc not available on PyPI, will use local analysis"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run uses PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
