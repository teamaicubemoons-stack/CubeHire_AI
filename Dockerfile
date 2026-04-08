# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
# We use --no-cache-dir to keep the image size small
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy model required for parsing
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY . .

# Ensure tokens directory exists for Gmail OAuth
RUN mkdir -p /app/Backend/tokens

# Expose the port the app runs on
# 7860 is the default port for Hugging Face Spaces
EXPOSE 7860

# Command to run the unified server
CMD ["python", "-m", "uvicorn", "Backend.app.unified_server:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips=*"]
