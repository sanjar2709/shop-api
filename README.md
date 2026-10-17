# shop-api

[![CI](https://github.com/sanjar2709/shop-api/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjar2709/shop-api/actions/workflows/ci.yml)

Backend for a small online store, built with Django and Django REST Framework.
It covers the usual flow: a customer browses the catalog, fills a cart, places an order,
and staff move the order from payment to delivery.

I built it as a portfolio project, but I tried to solve the problems a real shop runs into,
not just the CRUD part. The main one is stock: two people should never be able to buy the last item.

## What's inside

- **Auth**: email login with JWT, refresh token rotation, logout via token blacklist
- **Catalog**: categories and products, filters by category, price range and stock, search, ordering
- **Cart**: one cart per user, can't add more than what's in stock
- **Orders**: checkout from the cart, status flow `pending → paid → shipped → delivered`, cancellation
- **Background jobs**: order emails and auto-cancel for orders that weren't paid in 30 minutes (Celery + Redis)
- **Admin panel** for staff, **Swagger docs** at `/api/docs/`

Stack: Python 3.12, Django 6, DRF, PostgreSQL 17, Celery, Redis, pytest, Docker, GitHub Actions.

## How stock is protected

Checkout happens in one database transaction (`apps/orders/services.py`):

1. The product rows from the cart are locked with `SELECT ... FOR UPDATE`, in id order so two checkouts can't deadlock each other.
2. Stock is checked while the rows are locked. If something ran out, nothing is saved.
3. Stock is decreased with an `F()` expression, so the database does the math, not Python.
4. The order email is sent with `transaction.on_commit`, only after the order is really saved.

Product title and price are copied into the order items, so changing a product later doesn't change old orders.
When an order is cancelled, its items go back to stock.

There is a test for this: five threads try to buy the last item at the same moment, and only one of them gets it
(`test_last_item_cannot_be_sold_twice`).

The auto-cancel job has a similar check. Before it cancels an unpaid order, it locks the row and looks at the status again,
in case the customer paid a second ago.

## Running it

You need Docker. Copy the env file and fill in the values:

```bash
cp .env.example .env
```

**Everything in Docker:**

```bash
docker compose up -d
docker compose exec web python manage.py createsuperuser
```

API docs: http://localhost:8000/api/docs/, admin: http://localhost:8000/admin/

**Local development** (database and Redis in Docker, Django in a virtualenv):

```bash
docker compose up -d db redis
python -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

For background jobs, run these in separate terminals:

```bash
celery -A core worker -l info
celery -A core beat -l info
```

## API overview

| Method | Endpoint | Who |
|---|---|---|
| POST | `/api/v1/auth/register/` | anyone |
| POST | `/api/v1/auth/login/`, `/refresh/`, `/logout/` | anyone |
| GET, PATCH | `/api/v1/auth/me/` | user |
| GET | `/api/v1/categories/`, `/api/v1/products/` | anyone |
| POST, PATCH, DELETE | `/api/v1/categories/`, `/api/v1/products/` | staff |
| GET, DELETE | `/api/v1/cart/` | user |
| POST | `/api/v1/cart/items/` | user |
| PATCH, DELETE | `/api/v1/cart/items/{id}/` | user |
| GET, POST | `/api/v1/orders/` | user (staff sees all orders) |
| POST | `/api/v1/orders/{id}/cancel/` | user, only while pending |
| POST | `/api/v1/orders/{id}/status/` | staff |

Product filters: `?category=phones&min_price=100&max_price=500&in_stock=true&search=iphone&ordering=-price`

A quick example:

```bash
# log in
curl -X POST localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email": "me@example.com", "password": "..."}'

# add a product to the cart
curl -X POST localhost:8000/api/v1/cart/items/ \
  -H 'Authorization: Bearer <access token>' \
  -H 'Content-Type: application/json' \
  -d '{"product": "iphone-16", "quantity": 1}'

# place the order
curl -X POST localhost:8000/api/v1/orders/ \
  -H 'Authorization: Bearer <access token>' \
  -H 'Content-Type: application/json' \
  -d '{"shipping_address": "Tashkent, Chilonzor 1", "phone": "+998901234567"}'
```

## Tests

```bash
pytest --cov
```

45 tests, around 96% coverage. CI runs ruff and the test suite against PostgreSQL on every push,
and fails if coverage drops below 90%.

## Project layout

```
apps/
  common/    shared base model, permissions, test factories
  users/     custom user model with email login, auth endpoints
  catalog/   categories, products, filters
  cart/      cart and cart items
  orders/    orders, checkout logic (services.py), Celery tasks
core/        settings, urls, celery app
requirements/
  base.txt   what the app needs to run
  dev.txt    + pytest, ruff
  prod.txt   + gunicorn
```

Business logic for orders lives in `services.py`, not in views, so it can be used from the API, Celery tasks and tests the same way.

## License

MIT
