# Quick test script for OpenAI-only deployment
# Replace YOUR_OPENAI_KEY with your actual key from https://platform.openai.com/api-keys

$ServiceUrl = "https://orka-demo-647096874165.europe-west1.run.app"
$OpenAIKey = "sk-YOUR_OPENAI_KEY_HERE"  # ⚠️ REPLACE THIS!

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "Testing OrKa OpenAI-Only Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n[1] Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod "$ServiceUrl/api/health"
    Write-Host "✓ Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Simple Execution
Write-Host "`n[2] Testing with OpenAI..." -ForegroundColor Yellow
$body = @{
    input = "What is 2+2? Answer in one sentence."
    openai_api_key = $OpenAIKey
    yaml_config = @"
orchestrator:
  id: simple-test
  agents: [calc]

agents:
  - id: calc
    type: openai-answer
    model: gpt-4o-mini
    temperature: 0.0
    prompt: "{{ get_input() }}"
"@
} | ConvertTo-Json

try {
    Write-Host "Sending request..." -ForegroundColor Cyan
    $response = Invoke-RestMethod "$ServiceUrl/api/run" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "✓ Execution completed!" -ForegroundColor Green
    Write-Host "  Run ID: $($response.run_id)" -ForegroundColor Cyan
    
    # Parse the blob reference to get the actual response
    $events = $response.execution_log.events
    if ($events -and $events.Count -gt 0) {
        $blobRef = $events[0].payload.ref
        $blobStore = $response.execution_log.blob_store
        $actualResponse = $blobStore.$blobRef
        
        if ($actualResponse.response) {
            Write-Host "`n✓ AI Response: $($actualResponse.response)" -ForegroundColor Green
        } elseif ($actualResponse.error) {
            Write-Host "`n✗ Error: $($actualResponse.error)" -ForegroundColor Red
        }
    }
    
    # Download logs
    Write-Host "`n[3] Downloading logs..." -ForegroundColor Yellow
    $logUrl = "$ServiceUrl$($response.log_file_url)"
    $logFile = "trace_$($response.run_id).json"
    Invoke-RestMethod $logUrl -OutFile $logFile
    Write-Host "✓ Logs saved to: $logFile" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Execution failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $errorBody = $reader.ReadToEnd()
        Write-Host "`nError details: $errorBody" -ForegroundColor Red
    }
    exit 1
}

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "✓ All Tests Passed!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "`nYour OpenAI-only deployment is working!" -ForegroundColor Green
Write-Host "Service URL: $ServiceUrl" -ForegroundColor Cyan
Write-Host ""

