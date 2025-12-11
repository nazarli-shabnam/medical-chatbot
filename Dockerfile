FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Remove deprecated pinecone-plugin-inference if installed
# This plugin was deprecated in Pinecone SDK v6.0.0+ (inference is now built-in)
# It may be installed as a transitive dependency of pinecone-client==5.0.1
# Removing it prevents deprecation warnings and conflicts
RUN pip uninstall -y pinecone-plugin-inference 2>/dev/null || true

# Copy application code
COPY . .

# Create upload directory
RUN mkdir -p data/uploads

# Expose port
EXPOSE 8080

# Health check (using urllib instead of requests for reliability)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# Run the application
CMD ["python", "app.py"]
