# Build stage
FROM python:3.11-slim-bookworm AS builder

# Set work directory
WORKDIR /app

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install python dependencies to a specific target directory
RUN pip install --no-cache-dir --target=/app/site-packages -r requirements.txt

# Final stage using distroless
FROM gcr.io/distroless/python3-debian12

# Set work directory
WORKDIR /app

# Copy python dependencies
COPY --from=builder /app/site-packages /app/site-packages

# Copy application code
COPY src /app/src
COPY main.py /app/main.py
COPY configuration.yml /app/configuration.yml

# Check if there are other necessary folders/files
# For DataProfiler, we only need src/ and main.py for execution based on README.
# configuration.yml is optional but included.

# Set PYTHONPATH to include the site-packages directory
# Prepend /app/site-packages so it takes precedence, but keep /app for local modules
ENV PYTHONPATH=/app/site-packages:/app

# Set entrypoint to run main.py
ENTRYPOINT ["python", "/app/main.py"]
