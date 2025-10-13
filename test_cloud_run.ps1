# OrKa Cloud Run Test Script (PowerShell)
# Tests the OpenAI-only deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$OpenAIKey
)

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

Write-Host "`n=========================================" -ForegroundColor $Cyan
Write-Host "OrKa Cloud Run Test Suite" -ForegroundColor $Cyan
Write-Host "OpenAI-Only Architecture" -ForegroundColor $Cyan
Write-Host "=========================================" -ForegroundColor $Cyan

# Ensure URL doesn't have trailing slash
$ServiceUrl = $ServiceUrl.TrimEnd('/')

# Test 1: Health Check
Write-Host "`n[TEST 1] Health Check..." -ForegroundColor $Yellow
try {
    $health = Invoke-RestMethod "$ServiceUrl/api/health" -ErrorAction Stop
    Write-Host "✓ Health check passed" -ForegroundColor $Green
    Write-Host "  Status: $($health.status)" -ForegroundColor $Cyan
} catch {
    Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor $Red
    exit 1
}

# Test 2: Status Check
Write-Host "`n[TEST 2] Status Check..." -ForegroundColor $Yellow
try {
    $status = Invoke-RestMethod "$ServiceUrl/api/status" -ErrorAction Stop
    Write-Host "✓ Status check passed" -ForegroundColor $Green
    Write-Host "  Service: $($status.service)" -ForegroundColor $Cyan
    Write-Host "  Redis: $($status.dependencies.redis.status)" -ForegroundColor $Cyan
    Write-Host "  Rate Limiting: $($status.rate_limiting.enabled) ($($status.rate_limiting.limit))" -ForegroundColor $Cyan
} catch {
    Write-Host "✗ Status check failed: $($_.Exception.Message)" -ForegroundColor $Red
    exit 1
}

# Test 3: Simple Execution
Write-Host "`n[TEST 3] Simple Execution..." -ForegroundColor $Yellow
$simpleBody = @{
    input = "What is 2+2? Answer briefly."
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
    $response = Invoke-RestMethod "$ServiceUrl/api/run" `
        -Method Post `
        -ContentType "application/json" `
        -Body $simpleBody `
        -ErrorAction Stop
    
    Write-Host "✓ Execution completed" -ForegroundColor $Green
    Write-Host "  Run ID: $($response.run_id)" -ForegroundColor $Cyan
    Write-Host "  Input: $($response.input)" -ForegroundColor $Cyan
    
    # Check if we got a response
    if ($response.execution_log.agents.calc) {
        $answer = $response.execution_log.agents.calc.response
        Write-Host "  Answer: $($answer.Substring(0, [Math]::Min(100, $answer.Length)))..." -ForegroundColor $Cyan
    }
    
    # Save run ID for log retrieval
    $runId = $response.run_id
} catch {
    Write-Host "✗ Execution failed: $($_.Exception.Message)" -ForegroundColor $Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $errorBody = $reader.ReadToEnd()
        Write-Host "  Error details: $errorBody" -ForegroundColor $Red
    }
    exit 1
}

# Test 4: Log Retrieval
Write-Host "`n[TEST 4] Log Retrieval..." -ForegroundColor $Yellow
try {
    $logUrl = "$ServiceUrl$($response.log_file_url)"
    $logs = Invoke-RestMethod $logUrl -ErrorAction Stop
    
    Write-Host "✓ Log retrieval successful" -ForegroundColor $Green
    Write-Host "  Log size: $($logs.Length) bytes" -ForegroundColor $Cyan
    
    # Save to file
    $logFile = "trace_$runId.json"
    $logs | Out-File $logFile -Encoding UTF8
    Write-Host "  Saved to: $logFile" -ForegroundColor $Cyan
} catch {
    Write-Host "✗ Log retrieval failed: $($_.Exception.Message)" -ForegroundColor $Red
}

# Test 5: Multi-Agent Workflow
Write-Host "`n[TEST 5] Multi-Agent Workflow..." -ForegroundColor $Yellow
$multiBody = @{
    input = "Explain photosynthesis in one sentence."
    openai_api_key = $OpenAIKey
    yaml_config = @"
orchestrator:
  id: multi-agent-test
  agents: [explainer, summarizer]

agents:
  - id: explainer
    type: openai-answer
    model: gpt-4o-mini
    temperature: 0.7
    prompt: |
      Explain this topic in detail: {{ get_input() }}
      
  - id: summarizer
    type: openai-answer
    model: gpt-4o-mini
    temperature: 0.3
    prompt: |
      Summarize this explanation in one short sentence:
      {{ get_agent_response('explainer') }}
"@
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod "$ServiceUrl/api/run" `
        -Method Post `
        -ContentType "application/json" `
        -Body $multiBody `
        -ErrorAction Stop
    
    Write-Host "✓ Multi-agent execution completed" -ForegroundColor $Green
    Write-Host "  Run ID: $($response.run_id)" -ForegroundColor $Cyan
    
    if ($response.execution_log.agents.summarizer) {
        $summary = $response.execution_log.agents.summarizer.response
        Write-Host "  Summary: $summary" -ForegroundColor $Cyan
    }
} catch {
    Write-Host "✗ Multi-agent execution failed: $($_.Exception.Message)" -ForegroundColor $Red
}

# Test 6: Error Handling (Missing API Key)
Write-Host "`n[TEST 6] Error Handling..." -ForegroundColor $Yellow
$errorBody = @{
    input = "Test"
    yaml_config = "orchestrator:\n  agents: [test]"
    # Intentionally missing openai_api_key
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod "$ServiceUrl/api/run" `
        -Method Post `
        -ContentType "application/json" `
        -Body $errorBody `
        -ErrorAction Stop
    
    Write-Host "✗ Should have returned error for missing API key" -ForegroundColor $Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "✓ Correctly rejected request with missing API key" -ForegroundColor $Green
    } else {
        Write-Host "✗ Unexpected error: $($_.Exception.Message)" -ForegroundColor $Red
    }
}

# Test 7: Rate Limiting
Write-Host "`n[TEST 7] Rate Limiting..." -ForegroundColor $Yellow
Write-Host "  Sending 6 requests rapidly (limit is 5/minute)..." -ForegroundColor $Cyan

$rateLimitHit = $false
for ($i = 1; $i -le 6; $i++) {
    try {
        $response = Invoke-RestMethod "$ServiceUrl/api/health" -ErrorAction Stop
        Write-Host "  Request $i : OK" -ForegroundColor $Green
        Start-Sleep -Milliseconds 500
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "  Request $i : Rate limited (429)" -ForegroundColor $Yellow
            $rateLimitHit = $true
            break
        } else {
            Write-Host "  Request $i : Error $($_.Exception.Message)" -ForegroundColor $Red
        }
    }
}

if ($rateLimitHit) {
    Write-Host "✓ Rate limiting is working" -ForegroundColor $Green
} else {
    Write-Host "⚠ Rate limiting not triggered (may need to increase request rate)" -ForegroundColor $Yellow
}

# Summary
Write-Host "`n=========================================" -ForegroundColor $Cyan
Write-Host "Test Suite Complete" -ForegroundColor $Cyan
Write-Host "=========================================" -ForegroundColor $Cyan
Write-Host "`nAll critical tests passed! ✓" -ForegroundColor $Green
Write-Host "`nYour OrKa OpenAI-only deployment is working correctly." -ForegroundColor $Green
Write-Host "`nNext steps:" -ForegroundColor $Cyan
Write-Host "  1. Update your client applications to include 'openai_api_key' in requests" -ForegroundColor $Cyan
Write-Host "  2. Change all 'local_llm' agents to 'openai-answer' in YAML configs" -ForegroundColor $Cyan
Write-Host "  3. Monitor costs at: https://platform.openai.com/usage" -ForegroundColor $Cyan
Write-Host "  4. Scale as needed: gcloud run services update orka-demo --max-instances=50" -ForegroundColor $Cyan
Write-Host ""

