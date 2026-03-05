FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=task_service.settings

WORKDIR /app

# Install system dependencies (CRITICAL!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Expose port
EXPOSE 8002

# Run migrations and start
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn task_service.wsgi:application --bind 0.0.0.0:8002 --workers 2 --timeout 60"]

