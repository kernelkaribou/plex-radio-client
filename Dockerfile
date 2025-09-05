# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    pulseaudio \
    pulseaudio-utils \
    i2c-tools \
    python3-dev \
    python3-pip \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Create a non-root user for security
RUN useradd -m -u 1000 radio && chown -R radio:radio /app
USER radio

# Expose any ports if needed (not required for this app but good practice)
# EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]
