FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src ./src

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Expose port (for API service)
EXPOSE 8001

# Default command (overridden by docker-compose)
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8001"]
