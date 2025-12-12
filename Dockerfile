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

# Expose port (default, but will use PORT env var if set)
EXPOSE 8080

# Health check (using urllib instead of requests for reliability)
# Use PORT env var if available, otherwise default to 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/')" || exit 1

# Run the application with Gunicorn for production
# Gunicorn will use PORT environment variable if set (Render, Heroku, etc.)
# Otherwise defaults to 8080
# Using shell form to allow variable expansion
CMD gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app
