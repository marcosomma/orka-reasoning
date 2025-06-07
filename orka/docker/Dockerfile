FROM python:3.9-slim

WORKDIR /app

# Copy the entire project (build context is parent directory)
COPY . .

# Install minimal dependencies (avoid heavy ML packages for Docker)
RUN pip install --no-cache-dir -r orka/requirements-minimal.txt

# Install OrKa package in development mode
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Set PYTHONPATH to ensure modules can be found
ENV PYTHONPATH=/app

CMD ["python", "-m", "orka.server"] 