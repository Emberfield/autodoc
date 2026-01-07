#!/bin/bash
# Deploy Autodoc MCP Server to Google Cloud Run
#
# Usage:
#   ./scripts/deploy-mcp.sh [project-id] [region] [--lite]
#
# Options:
#   --lite    Use lightweight image (~200MB, keyword search only)
#             Default is full image (~3GB, includes semantic search)
#
# Example:
#   ./scripts/deploy-mcp.sh my-project us-central1
#   ./scripts/deploy-mcp.sh my-project us-central1 --lite

set -e

# Parse arguments
LITE_MODE=false
POSITIONAL_ARGS=()

for arg in "$@"; do
    case $arg in
        --lite)
            LITE_MODE=true
            shift
            ;;
        *)
            POSITIONAL_ARGS+=("$arg")
            ;;
    esac
done

PROJECT_ID=${POSITIONAL_ARGS[0]:-$(gcloud config get-value project 2>/dev/null)}
REGION=${POSITIONAL_ARGS[1]:-us-central1}
SERVICE_NAME="autodoc-mcp"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No project ID provided and no default project configured"
    echo "Usage: ./scripts/deploy-mcp.sh <project-id> [region] [--lite]"
    exit 1
fi

if [ "$LITE_MODE" = true ]; then
    DOCKERFILE="Dockerfile.mcp"
    echo "Using LIGHTWEIGHT image (~200MB, keyword search only)"
else
    DOCKERFILE="Dockerfile"
    echo "Using FULL image (~3GB, includes semantic search)"
fi

echo ""
echo "Deploying Autodoc MCP Server to Cloud Run"
echo "  Project:    $PROJECT_ID"
echo "  Region:     $REGION"
echo "  Service:    $SERVICE_NAME"
echo "  Dockerfile: $DOCKERFILE"
echo ""

# Build and push container image
echo "Building container image..."
if [ "$DOCKERFILE" != "Dockerfile" ]; then
    # gcloud builds submit only supports 'Dockerfile', so temporarily swap
    mv Dockerfile Dockerfile.full
    mv "$DOCKERFILE" Dockerfile
    trap "mv Dockerfile $DOCKERFILE; mv Dockerfile.full Dockerfile" EXIT
fi
gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID" .

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "MCP_TRANSPORT=sse"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)')

echo ""
echo "Deployment complete!"
echo ""
echo "MCP Server URL: $SERVICE_URL"
echo ""
echo "To connect from Claude Desktop, add to your MCP config:"
echo ""
echo '  "autodoc": {'
echo '    "transport": "sse",'
echo "    \"url\": \"$SERVICE_URL/sse\""
echo '  }'
