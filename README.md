# ShopKart Backend

Simple backend for an e-commerce project using Django REST Framework.

## Requirements
- Docker Desktop (recommended)
- Or Python 3.11, MySQL 8.0 (if running without Docker)

## Setup (Docker)
1. Copy env file
```
cp .env.example .env
```

2. Run
```
docker compose up --build
```

3. Create admin
```
docker compose exec web python manage.py createsuperuser
```

## Important URLs
- App: http://localhost:8000
- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:8000/swagger/
- Health: http://localhost:8000/health/

## Main APIs
### Auth
- POST /api/v1/auth/register/
- POST /api/v1/auth/login/
- POST /api/v1/auth/token/refresh/
- POST /api/v1/auth/logout/
- GET/PATCH /api/v1/auth/profile/
- PATCH /api/v1/auth/change-password/

### Products
- GET /api/v1/products/
- GET /api/v1/products/{slug}/
- GET /api/v1/products/categories/

### Orders
- GET /api/v1/orders/cart/
- POST /api/v1/orders/cart/items/
- POST /api/v1/orders/place_order/
- GET /api/v1/orders/

### Payments
- POST /api/v1/payments/initiate/
- POST /api/v1/payments/verify/
- GET /api/v1/payments/

### Reviews
- GET /api/v1/reviews/
- POST /api/v1/reviews/

## Logs
```
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f db
```

## Notes
- Payment is manual verify (no real gateway in backend).
- For vendor/admin APIs, you need proper roles.
