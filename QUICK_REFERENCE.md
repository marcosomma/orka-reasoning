# OrKa Cloud Run - Quick Reference Card

## 🚀 Deploy (3 Commands)

```bash
gcloud auth login && gcloud config set project YOUR_PROJECT_ID
bash deploy.sh
curl $(gcloud run services describe orka-demo --region eu-west1 --format 'value(status.url)')/api/health
```

## 🔗 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Service status |
| `/api/run` | POST | Execute workflow |
| `/api/logs/{run_id}` | GET | Download logs |

## 📊 Quick Stats

- **Deploy Time**: 35-45 minutes
- **Cost**: $25-$500/month (scales with usage)
- **Rate Limit**: 5 requests/minute/IP
- **Timeout**: 10 minutes per request
- **Resources**: 16GB RAM, 4 vCPU
- **Scaling**: 0-5 instances (auto)

## 🧪 Test Commands

```bash
# Get URL
URL=$(gcloud run services describe orka-demo --region eu-west1 --format 'value(status.url)')

# Health check
curl $URL/api/health

# Status check
curl $URL/api/status

# Execute workflow
curl -X POST $URL/api/run -H "Content-Type: application/json" -d @test_request.json

# Download logs (use run_id from above)
curl $URL/api/logs/YOUR_RUN_ID --output trace.json
```

## ⚙️ Configuration

```bash
# Environment Variables
ORKA_MEMORY_BACKEND=redisstack
REDIS_URL=redis://localhost:6380/0
ORKA_PORT=8000
OLLAMA_HOST=http://localhost:11434
ORKA_LOG_DIR=/logs
ORKA_LOG_RETENTION_HOURS=24
RATE_LIMIT_PER_MINUTE=5
```

## 🔧 Common Operations

### View Logs
```bash
gcloud run logs tail orka-demo --region eu-west1
```

### Update Service
```bash
bash deploy.sh
```

### Scale Up
```bash
gcloud run services update orka-demo --max-instances 10 --region eu-west1
```

### Change Rate Limit
```bash
gcloud run services update orka-demo --set-env-vars="RATE_LIMIT_PER_MINUTE=10" --region eu-west1
```

### Keep Warm (Reduce Cold Start)
```bash
gcloud run services update orka-demo --min-instances 1 --region eu-west1
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Build timeout | Increase to 2 hours: `--timeout=2h` |
| Out of memory | Increase RAM: `--memory 32Gi` |
| Cold start slow | Keep warm: `--min-instances 1` |
| Rate limited | Increase: `RATE_LIMIT_PER_MINUTE=10` |

## 📚 Documentation

- **Quick Start**: `CLOUD_RUN_QUICKSTART.md`
- **Full Guide**: `DEPLOYMENT.md`
- **Complete Details**: `DEPLOYMENT_COMPLETE.md`
- **File Inventory**: `DEPLOYMENT_FILES_INVENTORY.md`

## 📞 Help

- GitHub: https://github.com/marcosomma/orka-reasoning/issues
- Docs: https://orkacore.com/docs

