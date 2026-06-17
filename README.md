# SimpleCRM

A small, self-hostable CRM built with Django. Multi-workspace, soft-deletable,
and ready to drop behind nginx/Caddy/Traefik on a single VPS — or to run with
`docker compose up` for a quick local test.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](#)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](#)
[![Tailwind](https://img.shields.io/badge/Tailwind-4.x-38BDF8?logo=tailwindcss&logoColor=white)](#)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

> A minimal CRM for people who are tired of Salesforce's UI and just want to
> track contacts, companies and birthdays without selling a kidney.

---

## Table of contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Quick start (Docker)](#quick-start-docker)
- [Quick start (local Python)](#quick-start-local-python)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Available endpoints](#available-endpoints)
- [Security checklist](#security-checklist)
- [Tech stack](#tech-stack)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Multi-workspace** — one user belongs to one workspace; everything is scoped.
- **Contacts & companies** — full CRUD with UUID keys, search, and bulk delete.
- **Birthdays view** — see who is celebrating in the current month.
- **Soft delete** — nothing is ever lost (rows are flagged, not removed).
- **i18n** — English & Spanish out of the box, language switcher in settings.
- **Excel import / export** — bring your existing data in, take it back out.
- **Country / state / city pickers** — backed by throttled JSON search APIs.
- **Brute-force protection** — `django-axes`, 5 failed attempts → 1h lockout.
- **Production-ready by default** — secure cookies, HSTS, CSRF, clickjacking
  headers all switch on automatically when `DEBUG=False`.

---

## Screenshots
![Dashboard](https://i.imgur.com/wEWciG6.png)
![Contacts list](https://i.imgur.com/xlV9BRe.png)


---

## Quick start (Docker)

The fastest way to get a working instance. No Python, no virtualenvs, no tears.

### 1. Clone and configure

```bash
git clone https://github.com/Chaska-dev/AllCRM.git
cd AllCRM
cp .env.example .env
```

Open `.env` and set:

- `SECRET_KEY` — generate one with:
  ```bash
  docker run --rm python:3.12-slim python -c \
    "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `ALLOWED_HOSTS` — comma-separated, e.g. `crm.example.com,localhost`

### 2. Build and run (SQLite, zero external services)

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose logs -f web
```

Open <http://localhost:8000>. Done.

### 3. Or run with PostgreSQL

The compose file ships a `postgres` profile. Activate it with:

```bash
docker compose --profile postgres up -d --build
```

It will spin up a Postgres 16 container, create the schema on first run, and
mount the data into a named volume. To use an external Postgres, set
`DATABASE_URL=postgres://user:pass@host:5432/db` in `.env` and leave the
profile off.

### 4. Behind a reverse proxy (production)

Put nginx / Caddy / Traefik in front of the container and terminate TLS there.
`SECURE_SSL_REDIRECT`, HSTS and the `X-Forwarded-Proto` header trust are wired
up — you only need to add your hostname to `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`.

Minimal Caddy example:

```caddy
crm.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

---

## Quick start (local Python)

Prefer to run on bare metal? Same project, no container.

### Prerequisites

- Python **3.12+**
- System libs for Pillow (`libjpeg-dev`, `zlib1g-dev` on Debian/Ubuntu)

### Setup

```bash
git clone https://github.com/Chaska-dev/AllCRM.git
cd AllCRM
python -m venv venv

# Linux / macOS
source venv/bin/activate
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY (see command above)

python manage.py migrate
python manage.py tailwind install   # one-time: pulls the Tailwind CLI
python manage.py tailwind build     # builds the production CSS bundle
python manage.py createsuperuser
python manage.py runserver
```

Visit <http://127.0.0.1:8000>. For live CSS reload during development, run
`python manage.py tailwind start` in a second terminal.

---

## Configuration

All configuration is environment-driven. Copy `.env.example` and tweak.

| Variable              | Default                  | Notes                                            |
| --------------------- | ------------------------ | ------------------------------------------------ |
| `SECRET_KEY`          | **required**             | Django secret. Never commit a real one.          |
| `DEBUG`               | `False`                  | `True` for local dev only.                       |
| `ALLOWED_HOSTS`       | `localhost,127.0.0.1`    | Comma-separated hostnames Django will serve.     |
| `DATABASE_URL`        | empty (SQLite)           | `postgres://user:pass@host:port/db` for Postgres.|
| `CSRF_TRUSTED_ORIGINS`| empty                    | `https://crm.example.com` when behind HTTPS.     |
| `SECURE_COOKIES`      | `True`                   | Force secure cookies when not in DEBUG.          |

> `SECRET_KEY` is the only variable the app refuses to start without. Everything
> else has a safe default.

---

## Project layout

```
.
├── allcrm/              # Django project (settings, root urls, wsgi/asgi)
├── crm/                 # Main app: models, views, forms, import/export
├── theme/               # Tailwind v4 theme (django-tailwind integration)
├── templates/           # Project-level templates
├── static/              # Project-level static assets
├── media/               # User uploads (gitignored)
├── locale/              # Translation files (en, es)
├── dockerfile           # Multi-stage build (builder + runtime)
├── docker-compose.yaml  # web + optional postgres profile
├── manage.py
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Available endpoints

### HTML pages

| Path                       | Description                              |
| -------------------------- | ---------------------------------------- |
| `/login/`                  | Login form (with brute-force protection) |
| `/register/`               | Self-service registration                |
| `/logout/`                 | Logout (POST)                            |
| `/dashboard/`              | Authenticated landing page               |
| `/contacts/`               | Contact list, search, bulk delete        |
| `/contacts/create/`        | New contact                              |
| `/contacts/<uuid>/edit/`   | Edit contact                             |
| `/contacts/<uuid>/delete/` | Soft delete contact                      |
| `/companies/`              | Company list                             |
| `/companies/create/`       | New company                              |
| `/companies/<uuid>/edit/`  | Edit company                             |
| `/companies/<uuid>/delete/`| Soft delete company                      |
| `/birthdays/`              | This month's birthdays                   |
| `/settings/`               | User / workspace settings                |
| `/import-export/`          | Excel import & export                    |
| `/admin/`                  | Django admin                             |

### JSON API (versioned, throttled)

| Path                                  | Description                                |
| ------------------------------------- | ------------------------------------------ |
| `/api/v1/companies/search/?q=...`     | Typeahead search over companies            |
| `/api/v1/locations/countries/?q=...`  | Country search                             |
| `/api/v1/locations/states/`           | `?country=<id>&q=...`                      |
| `/api/v1/locations/cities/`           | `?state=<id>&q=...`                        |

Legacy aliases at `/api/...` are kept for compatibility and will be removed in a
future major release.

---

## Security checklist

What ships enabled out of the box:

- [x] `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` come from environment
- [x] Secure cookies + HSTS when `DEBUG=False`
- [x] `X-Frame-Options: DENY`
- [x] Login throttling (`django-axes`, 5 attempts / 1h)
- [x] CSRF on all state-changing views (POST-only for delete/bulk/logout)
- [x] Image upload validation (extension, magic bytes, size cap, anti-bomb)
- [x] Rate-limited JSON search endpoints
- [x] `SECURE_PROXY_SSL_HEADER` trust for reverse-proxy setups

---

## Tech stack

- **Backend** — Django 6, Python 3.12
- **Database** — SQLite by default, PostgreSQL when `DATABASE_URL` is set
- **WSGI** — gunicorn (3 workers)
- **Styling** — Tailwind CSS v4 via `django-tailwind`
- **Auth security** — `django-axes`
- **i18n** — Django's built-in translation framework (en, es)
- **Container** — multi-stage Dockerfile, `docker compose` with a postgres profile

---


## License

[MIT](LICENSE) — Copyright (c) 2026.
