FROM python:3.13-slim

WORKDIR /app/backend

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv && uv sync

# Copy the rest of the application code
COPY . .

# Create log directory
RUN mkdir -p /app/backend/logs

# Set PYTHONPATH to include /app so backend package can be imported
ENV PYTHONPATH=/app

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]