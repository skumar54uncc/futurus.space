#!/usr/bin/env bash
# Deploy Futurus API to Google Cloud Run (inline simulations).
# Prerequisites: gcloud CLI logged in, APIs enabled, Artifact Registry repo created.
#
# Usage:
#   export PROJECT_ID=your-gcp-project
#   export REGION=us-east1
#   ./deploy/cloudrun-deploy.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-east1}"
REPO="${REPO:-futurus}"
SERVICE="${SERVICE:-futurus-api}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:latest"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"

echo "Project=${PROJECT_ID} Region=${REGION} Image=${IMAGE}"

gcloud config set project "${PROJECT_ID}"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# Create Artifact Registry repo if missing (ignore error if exists)
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Futurus images" 2>/dev/null || true

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Building image from ${BACKEND} ..."
docker build -t "${IMAGE}" "${BACKEND}"
docker push "${IMAGE}"

echo "Deploying Cloud Run service ${SERVICE} ..."
gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --concurrency=1 \
  --max-instances=3 \
  --cpu-boost \
  --no-cpu-throttling \
  --set-env-vars="ENVIRONMENT=production,FUTURUS_SIMULATION_WORKER_INLINE=true,FUTURUS_RATE_LIMIT_STORAGE_URI=memory://"

echo "Done. Set secrets/env (DATABASE_URL, FIREWORKS_API_KEY, CLERK_*, REDIS_URL, BACKEND_URL, CORS_EXTRA_ORIGINS) next:"
echo "  gcloud run services update ${SERVICE} --region=${REGION} --set-env-vars=KEY=VALUE,..."
echo "Service URL:"
gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)'
