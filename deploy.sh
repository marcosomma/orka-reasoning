#!/bin/bash
# OrKa Google Cloud Run Deployment Script
# Automates the build and deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGION=${REGION:-"eu-west1"}
SERVICE_NAME=${SERVICE_NAME:-"orka-demo"}
MIN_INSTANCES=${MIN_INSTANCES:-0}
MAX_INSTANCES=${MAX_INSTANCES:-5}
MEMORY=${MEMORY:-"16Gi"}
CPU=${CPU:-4}
TIMEOUT=${TIMEOUT:-600}

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}OrKa Cloud Run Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project configured.${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${YELLOW}Using project:${NC} $PROJECT_ID"
echo -e "${YELLOW}Region:${NC} $REGION"
echo -e "${YELLOW}Service:${NC} $SERVICE_NAME"
echo ""

# Confirm deployment
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project=$PROJECT_ID

# Build container image using Cloud Build
echo -e "${YELLOW}Building container image (this may take 30-45 minutes)...${NC}"
echo "Building with Cloud Build..."
gcloud builds submit \
    --config cloudbuild.yaml \
    --timeout=1h \
    --project=$PROJECT_ID \
    --suppress-logs=false

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed. Please check the logs above.${NC}"
    exit 1
fi

echo -e "${GREEN}Build completed successfully!${NC}"

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/orka-demo:latest \
    --platform managed \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --min-instances $MIN_INSTANCES \
    --max-instances $MAX_INSTANCES \
    --allow-unauthenticated \
    --port 8000 \
    --set-env-vars="ORKA_MEMORY_BACKEND=redisstack,REDIS_URL=redis://localhost:6380/0,ORKA_PORT=8000,OLLAMA_HOST=http://localhost:11434,ORKA_LOG_DIR=/logs,ORKA_LOG_RETENTION_HOURS=24,RATE_LIMIT_PER_MINUTE=5" \
    --project=$PROJECT_ID

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed. Please check the logs above.${NC}"
    exit 1
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project=$PROJECT_ID \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Service URL:${NC} $SERVICE_URL"
echo ""
echo -e "${YELLOW}Test the deployment:${NC}"
echo "  curl $SERVICE_URL/api/health"
echo "  curl $SERVICE_URL/api/status"
echo ""
echo -e "${YELLOW}Monitor logs:${NC}"
echo "  gcloud run logs read $SERVICE_NAME --region $REGION --project $PROJECT_ID"
echo ""
echo -e "${YELLOW}Update deployment:${NC}"
echo "  ./deploy.sh"
echo ""
echo -e "${GREEN}Done!${NC}"

