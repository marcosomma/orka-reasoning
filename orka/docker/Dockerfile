FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the project
COPY . .

# Install the package with all dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[all]"

EXPOSE 8000

ENV PYTHONPATH=/app
ENV ORKA_MEMORY_BACKEND=redisstack

CMD ["python", "-m", "orka.server"] 