FROM python:3.11-slim

WORKDIR /app

# Install System dependencies
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip dependencies
RUN pip install --upgrade pip setuptools wheel

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8001

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]