# ---- Stage 1: build Tailwind + collectstatic -------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps for Pillow (libjpeg + zlib). No Node/npm needed:
# django-tailwind v4 ships a standalone CLI that builds Tailwind v4 in pure Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Tailwind v4 build + collect static files
# DEBUG must be False here so settings pick up production defaults
ENV DEBUG=False \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python manage.py tailwind build \
 && python manage.py collectstatic --noinput


# ---- Stage 2: minimal runtime ----------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system deps for Pillow only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy installed deps from the builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app
COPY --from=builder /app /app

# Collect static were already produced in the builder; this is a no-op safety net
ENV DEBUG=False \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root runtime user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

# Sensible gunicorn defaults for a small VPS
CMD ["gunicorn", "allcrm.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
