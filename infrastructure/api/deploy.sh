#!/bin/bash
# Deploy Autodoc Cloud API to Cloud Run
# Usage: ./deploy.sh [project-id]

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
SERVICE_NAME="autodoc-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Deploying Autodoc Cloud API to Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"

# Build the container
echo "Building container..."
docker build -t ${IMAGE_NAME}:latest .

# Push to GCR
echo "Pushing to Container Registry..."
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=https://iowgufboylypltycvwcp.supabase.co" \
  --set-env-vars "ALLOWED_ORIGINS=http://localhost:3000,https://autodoc.tools" \
  --set-secrets "SUPABASE_SERVICE_KEY=supabase-service-key:latest" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Store the Supabase service key in Secret Manager:"
echo "   gcloud secrets create supabase-service-key --data-file=-"
echo "2. Update your dashboard .env with:"
echo "   NEXT_PUBLIC_AUTODOC_API_URL=${SERVICE_URL}"
