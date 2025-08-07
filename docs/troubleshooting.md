# OrKa Troubleshooting Guide

This guide helps you diagnose and fix common issues in OrKa. For each problem, we provide:
- Symptoms to identify the issue
- Common causes
- Step-by-step solutions
- Prevention tips

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [RedisStack Issues](#redisstack-issues)
3. [Memory Performance](#memory-performance)
4. [Agent Execution](#agent-execution)
5. [Docker Issues](#docker-issues)
6. [API Integration](#api-integration)
7. [Production Deployment](#production-deployment)

## Installation Issues

### pip install fails

**Symptoms:**
- `pip install orka-reasoning` fails
- Dependency conflicts
- Version incompatibility errors

**Solutions:**

1. Check Python version:
```bash
python --version  # Should be 3.8 or higher
```

2. Create a fresh virtual environment:
```bash
python -m venv orka-env
source orka-env/bin/activate  # Linux/Mac
orka-env\Scripts\activate     # Windows
```

3. Upgrade pip:
```bash
pip install --upgrade pip
```

4. Install with explicit dependencies:
```bash
pip install orka-reasoning fastapi uvicorn kafka-python
```

### Import errors after installation

**Symptoms:**
- `ImportError: No module named 'orka'`
- `ModuleNotFoundError`

**Solutions:**

1. Verify installation:
```bash
pip list | grep orka
```

2. Check PYTHONPATH:
```bash
python -c "import sys; print(sys.path)"
```

3. Reinstall with verbose output:
```bash
pip install -v orka-reasoning
```

## RedisStack Issues

### "FT.CREATE unknown command"

**Symptoms:**
- `"unknown command 'FT.CREATE'"`
- Vector search not working
- Slow memory performance

**Causes:**
1. Using basic Redis instead of RedisStack
2. Docker not running
3. Wrong Redis connection URL

**Solutions:**

1. Verify RedisStack:
```bash
# Check if RedisStack is running
docker ps | grep redis-stack

# Check available commands
redis-cli FT._LIST
```

2. Start RedisStack properly:
```bash
docker run -d -p 6379:6379 redis/redis-stack:latest
```

3. Check connection URL:
```bash
export REDIS_URL=redis://localhost:6379/0
orka memory configure
```

### Memory Not Persisting

**Symptoms:**
- Data disappears after restart
- Inconsistent memory retrieval
- Missing historical interactions

**Solutions:**

1. Check Redis persistence:
```bash
redis-cli CONFIG GET save
```

2. Enable proper persistence:
```bash
redis-cli CONFIG SET save "60 1000"
```

3. Verify data directory:
```bash
docker inspect orka-redis | grep Source
```

## Memory Performance

### Slow Vector Search

**Symptoms:**
- Search takes >100ms
- High latency in memory operations
- Poor response times

**Solutions:**

1. Check HNSW configuration:
```bash
orka memory configure --show-hnsw
```

2. Optimize index parameters:
```yaml
# In your workflow YAML
memory_config:
  vector_params:
    M: 16
    ef_construction: 200
    ef_runtime: 10
```

3. Monitor performance:
```bash
orka memory watch --interval 1
```

### High Memory Usage

**Symptoms:**
- Redis memory warnings
- System slowdown
- OOM errors

**Solutions:**

1. Check memory usage:
```bash
redis-cli INFO memory
```

2. Clean up expired memories:
```bash
orka memory cleanup --dry-run
orka memory cleanup
```

3. Adjust decay settings:
```yaml
memory_config:
  decay:
    enabled: true
    default_short_term_hours: 2
    default_long_term_hours: 48
```

## Agent Execution

### Agent Timeouts

**Symptoms:**
- Workflow stops unexpectedly
- "Timeout waiting for agent" errors
- Incomplete execution

**Solutions:**

1. Check agent configuration:
```yaml
agents:
  - id: slow_agent
    type: openai-answer
    timeout: 300  # Increase timeout to 5 minutes
```

2. Monitor agent execution:
```bash
orka run workflow.yml --debug
```

3. Enable retries:
```yaml
orchestrator:
  retry_config:
    max_retries: 3
    backoff_factor: 2
```

### Invalid Agent Outputs

**Symptoms:**
- JSON parsing errors
- Template rendering failures
- Agent chain breaks

**Solutions:**

1. Validate agent output:
```bash
orka validate workflow.yml
```

2. Add error handling:
```yaml
agents:
  - id: problematic_agent
    type: openai-answer
    error_handling:
      fallback_response: "Default response if failed"
      retry_on_error: true
```

## Docker Issues

### Container Communication

**Symptoms:**
- Services can't connect
- Network timeouts
- DNS resolution failures

**Solutions:**

1. Check Docker network:
```bash
docker network ls
docker network inspect orka_default
```

2. Verify service discovery:
```bash
docker-compose ps
docker-compose logs orka
```

3. Test connectivity:
```bash
docker exec orka-redis redis-cli ping
```

### Resource Constraints

**Symptoms:**
- Container crashes
- Out of memory errors
- CPU throttling

**Solutions:**

1. Check resource usage:
```bash
docker stats
```

2. Adjust limits:
```yaml
# docker-compose.yml
services:
  redis-stack:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

## API Integration

### OpenAI API Issues

**Symptoms:**
- API key errors
- Rate limiting
- Timeout errors

**Solutions:**

1. Verify API key:
```bash
export OPENAI_API_KEY=your-key-here
orka validate-key
```

2. Handle rate limits:
```yaml
agents:
  - id: gpt_agent
    type: openai-answer
    rate_limit:
      max_requests: 60
      per_minute: true
```

3. Enable fallbacks:
```yaml
orchestrator:
  api_fallbacks:
    enabled: true
    local_llm_backup: true
```

## Production Deployment

### Kafka Integration

**Symptoms:**
- Message loss
- Partition errors
- Consumer lag

**Solutions:**

1. Check Kafka status:
```bash
orka-kafka status
```

2. Monitor topics:
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --list
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe
```

3. Optimize settings:
```yaml
# kafka-config.yml
memory_config:
  kafka:
    num_partitions: 12
    replication_factor: 3
    retention_ms: 604800000  # 1 week
```

### Monitoring and Alerts

**Symptoms:**
- Missing metrics
- Late alerts
- Incomplete logs

**Solutions:**

1. Enable comprehensive monitoring:
```bash
orka monitor --enable-metrics --enable-tracing
```

2. Configure alerts:
```yaml
# monitoring-config.yml
alerts:
  memory_usage:
    threshold: 80
    window: 5m
  api_errors:
    threshold: 5
    window: 1m
```

3. Set up logging:
```bash
orka logs --level debug --output /var/log/orka/
```

## Getting More Help

If you're still experiencing issues:

1. Check our [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)
2. Join our [Discord community](https://discord.gg/orka)
3. Read the [FAQ](./faq.md)
4. Contact support: support@orkacore.com

## Contributing

Found a bug or have a fix? We welcome contributions!

1. Open an issue describing the problem
2. Fork the repository
3. Submit a pull request with your fix
4. Include tests and documentation

See our [Contributing Guide](../CONTRIBUTING.md) for more details.