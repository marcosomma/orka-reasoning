FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project (build context is parent directory)
COPY . .

# Install core dependencies for V0.7.0
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    redis[async]>=5.0.0 \
    pyyaml>=6.0 \
    fastapi>=0.68.0 \
    uvicorn>=0.15.0 \
    python-dotenv>=0.19.0 \
    jinja2>=3.0.0 \
    openai>=1.0.0 \
    litellm>=1.0.0 \
    duckduckgo-search>=3.0.0 \
    google-api-python-client>=2.0.0 \
    async-timeout>=4.0.0 \
    rich>=13.0.0 \
    textual>=0.40.0 \
    kafka-python>=2.0.2 \
    confluent-kafka[avro,protobuf,schema-registry] \
    avro-python3 \
    fastavro \
    protobuf \
    jsonschema \
    sentence-transformers>=2.2.0 \
    numpy>=1.21.0

# Install OrKa package in development mode
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Set PYTHONPATH to ensure modules can be found
ENV PYTHONPATH=/app

# Default to RedisStack backend for V0.7.0
ENV ORKA_MEMORY_BACKEND=redisstack

CMD ["python", "-m", "orka.server"] 