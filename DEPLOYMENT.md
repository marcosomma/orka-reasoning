# OrKa Google Cloud Run Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying OrKa with GPT-oss:20B to Google Cloud Run as a public demo API with rate limiting and log retrieval.

## Architecture

### All-in-One Container
- **Base**: Ubuntu 22.04 with Python 3.11
- **Components**: Redis + Ollama + GPT-oss:20B + OrKa
- **Size**: ~15-20GB (includes LLM model)
- **Startup**: Multi-process coordination via startup script

### Cloud Run Configuration
- **CPU**: 4 vCPU
- **Memory**: 16GB RAM
- **Scaling**: 0-5 instances (auto-scaling)
- **Timeout**: 10 minutes per request
- **Concurrency**: 10 requests per container
- **Rate Limit**: 5 requests/minute per IP

### API Endpoints
1. `POST /api/run` - Execute workflow
2. `GET /api/logs/{run_id}` - Download execution trace
3. `GET /api/health` - Health check
4. `GET /api/status` - Detailed status (Redis, Ollama, rate limits)

## Prerequisites

### 1. Google Cloud Account
```bash
# Install Google Cloud SDK
# macOS: 
brew install google-cloud-sdk

# Linux:
curl https://sdk.cloud.google.com | bash

# Windows:
# Download from https://cloud.google.com/sdk/docs/install
```

### 2. Project Setup
```bash
# Login to Google Cloud
gcloud auth login

# Create new project (or use existing)
gcloud projects create orka-demo-12345 --name="OrKa Demo"

# Set active project
gcloud config set project orka-demo-12345

# Enable billing (required for Cloud Run)
# Visit: https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com
```

### 3. Verify Setup
```bash
# Check project
gcloud config get-value project

# Check active account
gcloud config get-value account

# Check region
gcloud config get-value run/region
# If not set:
gcloud config set run/region eu-west1
```

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

```bash
# 1. Make deploy script executable
chmod +x deploy.sh

# 2. Run deployment
./deploy.sh

# This will:
# - Validate gcloud configuration
# - Enable required APIs
# - Build container image (~30-45 minutes)
# - Deploy to Cloud Run
# - Display service URL
```

### Option 2: Manual Deployment

#### Step 1: Build Container Image

```bash
# Build using Cloud Build (recommended)
gcloud builds submit \
    --config cloudbuild.yaml \
    --timeout=1h

# OR build locally (requires Docker with 16GB+ RAM)
docker build -f Dockerfile.cloudrun -t gcr.io/PROJECT_ID/orka-demo:latest .
docker push gcr.io/PROJECT_ID/orka-demo:latest
```

#### Step 2: Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy orka-demo \
    --image gcr.io/PROJECT_ID/orka-demo:latest \
    --platform managed \
    --region eu-west1 \
    --memory 16Gi \
    --cpu 4 \
    --min-instances 0 \
    --max-instances 5 \
    --timeout 600 \
    --allow-unauthenticated \
    --port 8000

# Get service URL
gcloud run services describe orka-demo \
    --region eu-west1 \
    --format 'value(status.url)'
```

## Testing the Deployment

### 1. Health Check

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe orka-demo \
    --region eu-west1 \
    --format 'value(status.url)')

# Check health
curl $SERVICE_URL/api/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "orka-api",
#   "version": "1.0.0",
#   "timestamp": "2025-01-15T10:30:00.000000"
# }
```

### 2. Status Check

```bash
# Check detailed status
curl $SERVICE_URL/api/status

# Expected response includes:
# - Redis connection status
# - Ollama status and loaded models
# - Rate limiting configuration
```

### 3. Execute Workflow

```bash
# Using test_request.json
curl -X POST $SERVICE_URL/api/run \
    -H "Content-Type: application/json" \
    -d @test_request.json

# OR inline example
curl -X POST $SERVICE_URL/api/run \
    -H "Content-Type: application/json" \
    -d '{
        "input": "What is machine learning?",
        "yaml_config": "orchestrator:\n  id: simple-qa\n  agents: [qa_agent]\n\nagents:\n  - id: qa_agent\n    type: local_llm\n    model: gpt-oss:20b\n    model_url: http://localhost:11434/api/generate\n    provider: ollama\n    prompt: \"Answer this question: {{ get_input() }}\""
    }'

# Response includes:
# {
#   "run_id": "abc-123-def-456",
#   "input": "...",
#   "execution_log": {...},
#   "log_file_url": "/api/logs/abc-123-def-456",
#   "timestamp": "..."
# }
```

### 4. Download Logs

```bash
# Extract run_id from execution response
RUN_ID="abc-123-def-456"

# Download execution trace
curl $SERVICE_URL/api/logs/$RUN_ID \
    --output trace.json

# View trace
cat trace.json | jq .
```

## Client Integration Examples

### Python Client

```python
import requests
import json
from pathlib import Path

class OrkaClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def execute_workflow(self, input_text, yaml_config):
        """Execute OrKa workflow"""
        response = requests.post(
            f"{self.base_url}/api/run",
            json={
                "input": input_text,
                "yaml_config": yaml_config
            },
            timeout=600  # 10 minutes
        )
        response.raise_for_status()
        return response.json()
    
    def download_logs(self, run_id, output_path):
        """Download execution logs"""
        response = requests.get(
            f"{self.base_url}/api/logs/{run_id}"
        )
        response.raise_for_status()
        
        with open(output_path, 'w') as f:
            json.dump(response.json(), f, indent=2)
        
        return output_path
    
    def health_check(self):
        """Check service health"""
        response = requests.get(f"{self.base_url}/api/health")
        return response.json()

# Usage
client = OrkaClient("https://orka-demo-xxxxx.run.app")

# Execute workflow
result = client.execute_workflow(
    input_text="Explain quantum computing",
    yaml_config=Path("my_workflow.yml").read_text()
)

print(f"Run ID: {result['run_id']}")
print(f"Response: {result['execution_log']}")

# Download logs
client.download_logs(
    run_id=result['run_id'],
    output_path=f"trace_{result['run_id']}.json"
)
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

class OrkaClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    async executeWorkflow(inputText, yamlConfig) {
        const response = await axios.post(
            `${this.baseUrl}/api/run`,
            {
                input: inputText,
                yaml_config: yamlConfig
            },
            { timeout: 600000 } // 10 minutes
        );
        return response.data;
    }

    async downloadLogs(runId, outputPath) {
        const response = await axios.get(
            `${this.baseUrl}/api/logs/${runId}`,
            { responseType: 'json' }
        );
        
        fs.writeFileSync(
            outputPath,
            JSON.stringify(response.data, null, 2)
        );
        
        return outputPath;
    }

    async healthCheck() {
        const response = await axios.get(`${this.baseUrl}/api/health`);
        return response.data;
    }
}

// Usage
const client = new OrkaClient('https://orka-demo-xxxxx.run.app');

(async () => {
    // Execute workflow
    const yamlConfig = fs.readFileSync('my_workflow.yml', 'utf8');
    const result = await client.executeWorkflow(
        'Explain quantum computing',
        yamlConfig
    );
    
    console.log(`Run ID: ${result.run_id}`);
    
    // Download logs
    await client.downloadLogs(
        result.run_id,
        `trace_${result.run_id}.json`
    );
})();
```

### curl Script

```bash
#!/bin/bash
# orka-client.sh - Simple curl-based client

SERVICE_URL="https://orka-demo-xxxxx.run.app"

# Execute workflow
execute_workflow() {
    local input="$1"
    local yaml_file="$2"
    
    local yaml_config=$(cat "$yaml_file")
    
    curl -X POST "$SERVICE_URL/api/run" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
    "input": "$input",
    "yaml_config": $(echo "$yaml_config" | jq -Rs .)
}
EOF
}

# Download logs
download_logs() {
    local run_id="$1"
    local output_file="${2:-trace_${run_id}.json}"
    
    curl "$SERVICE_URL/api/logs/$run_id" \
        --output "$output_file"
    
    echo "Logs saved to $output_file"
}

# Usage
# ./orka-client.sh
```

## Monitoring & Maintenance

### View Logs

```bash
# Real-time logs
gcloud run logs tail orka-demo --region eu-west1

# Recent logs
gcloud run logs read orka-demo \
    --region eu-west1 \
    --limit 100

# Filter by severity
gcloud run logs read orka-demo \
    --region eu-west1 \
    --filter "severity>=ERROR"
```

### Monitor Metrics

```bash
# View in Cloud Console
echo "https://console.cloud.google.com/run/detail/eu-west1/orka-demo/metrics"

# Or use gcloud
gcloud monitoring dashboards list
```

### Update Deployment

```bash
# Rebuild and redeploy
./deploy.sh

# OR manually
gcloud builds submit --config cloudbuild.yaml --timeout=1h
gcloud run deploy orka-demo \
    --image gcr.io/PROJECT_ID/orka-demo:latest \
    --region eu-west1
```

### Scale Configuration

```bash
# Adjust min/max instances
gcloud run services update orka-demo \
    --region eu-west1 \
    --min-instances 1 \
    --max-instances 10

# Adjust memory/CPU
gcloud run services update orka-demo \
    --region eu-west1 \
    --memory 32Gi \
    --cpu 8
```

## Cost Management

### Estimated Costs (Monthly)

| Scenario | Compute Hours | Cost |
|----------|--------------|------|
| **Light** (10% usage) | ~36 hours | ~$25 |
| **Medium** (50% usage) | ~180 hours | ~$125 |
| **Heavy** (constant 2 instances) | ~720 hours | ~$500 |

**Breakdown per instance-hour:**
- 4 vCPU + 16GB RAM = ~$0.70/hour
- Container Registry: ~$2/month
- Network egress: ~$0.12/GB

### Cost Optimization

```bash
# 1. Set budget alerts
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="OrKa Budget" \
    --budget-amount=300USD

# 2. Enable scale-to-zero (already default)
# Instances shut down when idle

# 3. Limit max instances
gcloud run services update orka-demo \
    --max-instances 3 \
    --region eu-west1

# 4. Monitor costs
gcloud billing accounts describe BILLING_ACCOUNT_ID
```

## Troubleshooting

### Container Fails to Start

```bash
# Check logs
gcloud run logs read orka-demo --region eu-west1 --limit 50

# Common issues:
# - Ollama model download timeout: Increase startup timeout
# - Redis connection failed: Check startup script
# - Out of memory: Increase memory allocation
```

### Model Download Issues

```bash
# The model downloads at startup. To pre-bake into image:
# Edit Dockerfile.cloudrun, uncomment model download step
# Rebuild: gcloud builds submit --timeout=2h
```

### Rate Limit Too Restrictive

```bash
# Update rate limit
gcloud run services update orka-demo \
    --region eu-west1 \
    --set-env-vars="RATE_LIMIT_PER_MINUTE=10"
```

### High Latency

```bash
# Increase min instances (keep warm)
gcloud run services update orka-demo \
    --region eu-west1 \
    --min-instances 1

# Or enable CPU boost
gcloud run services update orka-demo \
    --region eu-west1 \
    --cpu-boost
```

## Security Considerations

### Current Security Profile
- ✅ Rate limiting (5 req/min per IP)
- ✅ Input validation (100KB YAML limit)
- ✅ Timeout protection (10min)
- ⚠️ No authentication (public demo)
- ⚠️ No request logging/audit trail

### Hardening for Production

```bash
# 1. Add authentication
gcloud run services update orka-demo \
    --region eu-west1 \
    --no-allow-unauthenticated

# 2. Add Cloud Armor (WAF)
# Requires Load Balancer setup

# 3. Implement API keys
# Add middleware in orka/server.py

# 4. Enable audit logging
gcloud logging sinks create orka-audit \
    pubsub.googleapis.com/projects/PROJECT_ID/topics/orka-audit
```

## Cleanup

### Delete Service

```bash
# Delete Cloud Run service
gcloud run services delete orka-demo \
    --region eu-west1

# Delete container images
gcloud container images delete gcr.io/PROJECT_ID/orka-demo:latest
```

### Delete Project

```bash
# WARNING: This deletes EVERYTHING in the project
gcloud projects delete orka-demo-12345
```

## Support

- **Documentation**: https://orkacore.com/docs
- **GitHub**: https://github.com/marcosomma/orka-reasoning
- **Issues**: https://github.com/marcosomma/orka-reasoning/issues

## License

OrKa is licensed under Apache 2.0. See LICENSE file for details.

