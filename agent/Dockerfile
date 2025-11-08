FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js and npm for Claude Code CLI
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src ./src

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@2.0.35

# Expose port (for API service)
EXPOSE 8001

# Default command (overridden by docker-compose)
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8001"]
