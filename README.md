# CRM

A small, self-hostable CRM built with Django. Designed to be deployed behind a
reverse proxy (nginx/Caddy/Traefik) on a single VPS.

## Features

- Multi-workspace (one user belongs to one workspace)
- Contacts and companies with full CRUD
- Soft delete (no data loss)
- JSON search endpoints (companies, countries, states, cities)
- Brute-force protection via `django-axes`
- CSRF and secure-cookie enforcement in production

## Quick start (local development)

```bash
python -m venv venv
. venv/Scripts/activate     # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set SECRET_KEY (you can generate one with):
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

python manage.py migrate
python manage.py tailwind install
python manage.py tailwind build
python manage.py runserver
```

Default database is SQLite. No external service required.

## Switching to PostgreSQL

Set `DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DB` in `.env` and add
`psycopg2-binary` to `requirements.txt`. The settings module will pick it up
automatically; leave it empty to stay on SQLite.

## Production deployment (Docker)

```bash
cp .env.example .env
# Set SECRET_KEY and ALLOWED_HOSTS in .env
docker compose --profile postgres up -d   # include Postgres
# or
docker compose up -d                       # SQLite only
```

The image runs `gunicorn` on port 8000. Put it behind nginx/Caddy with TLS
(`SECURE_SSL_REDIRECT` is enabled automatically when `DEBUG=False`).

## Security checklist

- [x] `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` come from environment
- [x] Secure cookies + HSTS when not in DEBUG
- [x] `X_FRAME_OPTIONS=DENY`
- [x] Login throttling (`django-axes`, 5 attempts / 1h)
- [x] CSRF on all state-changing views (POST only for delete/bulk/logout)
- [x] Image upload validation (extension, magic bytes, size cap, anti-bomb)
- [x] Rate-limited JSON search endpoints (`/api/v1/...`)

## URLs

- `/login/`, `/register/`, `/logout/`
- `/dashboard/`, `/contacts/`, `/companies/`
- `/api/v1/companies/search/?q=...`
- `/api/v1/locations/countries/?q=...&lang=es`
- `/api/v1/locations/states/?country=<id>&q=...`
- `/api/v1/locations/cities/?state=<id>&q=...`
- `/admin/`

Legacy aliases at `/api/...` are kept for compatibility and will be removed in
a future release.
