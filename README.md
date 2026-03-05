# ShopKart Backend

Beginner‑friendly backend for a multi‑vendor e‑commerce project using Django REST Framework.

## Quick Start (Docker – Recommended)
1. Copy env file
```bash
cp .env.example .env
```

2. Start services (MySQL + Redis + Web + Celery)
```bash
docker compose up --build
```

3. Create admin user
```bash
docker compose exec web python manage.py createsuperuser
```

4. Open the app
- App: http://localhost:8000
- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:8000/swagger/
- Health: http://localhost:8000/health/

## Local Setup (Without Docker)
### Requirements
- Python 3.11+
- MySQL 8.0+
- Redis (for cache + Celery)

### Steps
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running Tests
Local:
```bash
pytest -q
```
Docker:
```bash
docker compose exec -T web pytest -q
```

## Core API Endpoints
### Auth
- POST `/api/v1/auth/register/`
- POST `/api/v1/auth/login/`
- POST `/api/v1/auth/token/refresh/`
- POST `/api/v1/auth/logout/`
- GET/PATCH `/api/v1/auth/profile/`
- PATCH `/api/v1/auth/change-password/`
- POST `/api/v1/auth/email/verify/request/`
- POST `/api/v1/auth/email/verify/`
- POST `/api/v1/auth/password-reset/request/`
- POST `/api/v1/auth/password-reset/confirm/`

### Products & Categories
- GET `/api/v1/products/`
- GET `/api/v1/products/{slug}/`
- GET `/api/v1/products/?q=search-term`
- GET `/api/v1/products/categories/`

### Vendors
- GET `/api/v1/vendors/`
- GET `/api/v1/vendors/{slug}/`
- GET `/api/v1/vendors/dashboard/` (vendor only)

### Orders & Cart
- GET `/api/v1/orders/cart/`
- POST `/api/v1/orders/cart/items/`
- POST `/api/v1/orders/place_order/`
- GET `/api/v1/orders/`
- POST `/api/v1/orders/returns/`
- PATCH `/api/v1/orders/returns/{id}/update_status/`

### Payments
- POST `/api/v1/payments/initiate/`
- POST `/api/v1/payments/verify/`
- POST `/api/v1/payments/webhook/`
- GET `/api/v1/payments/`

### Reviews
- GET `/api/v1/reviews/`
- POST `/api/v1/reviews/`
- GET `/api/v1/reviews/stats/?product_id=...`
- POST `/api/v1/reviews/{id}/reply/` (vendor/admin)
- POST `/api/v1/reviews/{id}/report/`
- GET `/api/v1/reviews/vendor_reviews/`
- GET `/api/v1/reviews/export/?format=csv|json`
- GET `/api/v1/reviews/reports/` (admin)

## Background Jobs (Celery)
Celery runs automatically in Docker.  
Locally:
```bash
celery -A config.celery app worker -l info
```

## Env Quick Guide
Important `.env` values:
- `DB_*` for MySQL
- `REDIS_URL` for cache + celery
- `PAYMENT_WEBHOOK_SECRET` for webhook signature
- `EMAIL_*` for email sending

## Logs
```bash
docker compose logs -f web
docker compose logs -f celery
docker compose logs -f db
docker compose logs -f redis
```

## Notes
- Payments are simulated (no live gateway).
- Vendor/Admin endpoints require proper role.
