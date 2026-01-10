FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock* ./

# Copy application code (needed for installation)
COPY glueprompt/ ./glueprompt/
COPY examples/ ./examples/

# Install the package and dependencies
RUN uv pip install --system -e .

# Create directories for cache and config
RUN mkdir -p /root/.cache/glueprompt/repos \
    /root/.cache/glueprompt/worktrees \
    /root/.config/glueprompt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GLUEPROMPT_LOG_LEVEL=INFO

# Expose default server port
EXPOSE 8000

# Default command: start the FastAPI server
# Override in docker-compose or run command to use CLI instead
CMD ["glueprompt", "serve", "--host", "0.0.0.0", "--port", "8000"]
