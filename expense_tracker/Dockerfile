FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files (if any)
# RUN python manage.py collectstatic --noinput

# Final stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app /app

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "expense_tracker.wsgi:application", "--bind", "0.0.0.0:8000"]
