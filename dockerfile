FROM python:3.12-slim

WORKDIR /app

# Build deps for Pillow + node for tailwind
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node deps
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Build Tailwind
RUN python manage.py tailwind build

# Collect static (DEBUG is forced False during build via env)
ENV DEBUG=False
RUN python manage.py collectstatic --noinput

# Run as non-root
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "allcrm.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
