# OrKa Cloud Run - Quick Start

## 🚀 Deploy in 3 Steps

### 1. Setup Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 2. Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. Test
```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe orka-demo --region eu-west1 --format 'value(status.url)')

# Health check
curl $SERVICE_URL/api/health

# Run a workflow
curl -X POST $SERVICE_URL/api/run \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## 📋 What You Get

- **REST API** for OrKa workflows
- **GPT-oss:20B** model running on Ollama
- **Rate limiting** (5 requests/min per IP)
- **Log downloads** via `/api/logs/{run_id}`
- **Auto-scaling** (0-5 instances)
- **$0 when idle** (scales to zero)

## 🔗 API Endpoints

- `POST /api/run` - Execute workflow
- `GET /api/logs/{run_id}` - Download logs
- `GET /api/health` - Health check
- `GET /api/status` - Detailed status

## 📊 Cost Estimate

- **Light usage** (10%): ~$25/month
- **Medium usage** (50%): ~$125/month
- **Heavy usage** (always on): ~$500/month

## 📚 Full Documentation

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

## 🛠️ Troubleshooting

**Build fails?**
```bash
# Check Cloud Build logs
gcloud builds list --limit 5
```

**Service unhealthy?**
```bash
# Check logs
gcloud run logs tail orka-demo --region eu-west1
```

**Rate limited?**
```bash
# Increase limit
gcloud run services update orka-demo \
  --set-env-vars="RATE_LIMIT_PER_MINUTE=10" \
  --region eu-west1
```

## 📞 Support

- Docs: https://orkacore.com/docs
- Issues: https://github.com/marcosomma/orka-reasoning/issues

