FROM python:3.9-slim

WORKDIR /app

# Install the package and its dependencies
RUN pip install orka-reasoning

# Copy the docker configuration files
COPY docker-compose.yml .
COPY Dockerfile .

# Show what was copied
RUN echo "=== Contents of /app ===" && ls -la && echo "=== End of contents ==="

EXPOSE 8000

CMD ["python", "-m", "orka.server"] 