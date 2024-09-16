# Use a slim Python runtime as a parent image
FROM python:3.12-slim

# Additional fixing installation for Postgres, needed to work with db with Linux system
RUN apt-get update && apt-get install -y libpq-dev
# Installing netcat
RUN apt-get update && apt-get install -y netcat-openbsd

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list > /dev/null \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libx11-6

RUN apt-get update && apt-get install -y xvfb

# Create a working directory
WORKDIR /app

# Copy and install requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files to the container
COPY . /app

# Create media directory
RUN mkdir -p /app/media/coins /app/media/pools /app/media/chains

# Ensure start.sh has executable permissions
RUN chmod +x /app/start.sh

# Set the entrypoint to start.sh
ENTRYPOINT ["/app/start.sh"]