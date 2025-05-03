FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /app

# Show what was copied
RUN echo "=== Contents of /app ===" && ls -la && echo "=== End of contents ==="

# Install the package
WORKDIR /app
RUN pip install -e .

EXPOSE 8000

CMD ["python", "-m", "orka.server"] 