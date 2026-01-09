#!/bin/bash
# Run Autodoc Cloud API locally for development
# Usage: ./run_local.sh

set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check required env vars
if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "Error: SUPABASE_SERVICE_KEY not set"
    echo "Copy .env.example to .env and fill in your values"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Run the server
echo "Starting Autodoc Cloud API on http://localhost:8080"
python main.py
