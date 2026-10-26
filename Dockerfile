FROM python:3.11-slim

# Install system dependencies (FFmpeg is required for audio mixing and encoding)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user (Hugging Face Spaces default UID is 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=7860

WORKDIR $HOME/app

# Install Python dependencies first for caching
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY --chown=user:user . .

# Ensure audio cache, static, and templates directories exist with write permissions
RUN mkdir -p audio_cache audio_cache/prerendered static templates && \
    chmod -R 777 audio_cache static templates

# Switch to non-root user
USER user

# Expose default port
EXPOSE 7860

# Start Radio Four D M master station
CMD ["python", "app.py"]
