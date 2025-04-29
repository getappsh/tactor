# Connection Manager Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    net-tools \
    iproute2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the connection manager script
COPY connection_manager.py .

# Set entrypoint
ENTRYPOINT ["python", "connection_manager.py"]
