# Product Catalog (Django take-home)

## Project description

A Django project that models **products, categories and tags**, is populated through the **Django admin**, and offers an HTML page to **search products by description and filter them by category and tags**, with all options combinable. It was built for the take-home assignment in [`ASSIGNMENT.md`](ASSIGNMENT.md).

Beyond the brief it adds a nested category tree, stock and prices, favourites, one-click checkout, a JSON API with OpenAPI docs, JWT authentication, caching and security hardening.

**Scope note:** the brief asks for a few hours of work; this goes well beyond it. The required core (models and relationships, admin data entry, the search and filter page, fixtures, README) was built and tested first, and the extensions were added on top in separate steps. Each step is recorded in `openspec/changes/archive/2026-11-22-product-catalog/tasks.md`.

**Stack:** Python 3.12+ (developed on 3.14), Django 5.2 LTS, SQLite, Django REST framework, django-filter, drf-spectacular, djangorestframework-simplejwt, django-cors-headers, managed with [uv](https://docs.astral.sh/uv/).

## Features

- [x] Category tree with configurable depth
- [x] Products and tags managed in the admin
- [x] Search and combinable filters
- [x] Storefront page, product pages and pictures
- [x] Sign-up and login by email
- [x] Demo data fixtures
- [x] Favourites
- [x] One-click checkout and order history
- [x] JSON API with Swagger docs
- [x] JWT authentication for the API
- [x] Web security (CSRF, CORS, settings from the environment)

## Workflow

### User workflow

1. **An administrator manages the catalog** at `/admin/` (demo login `admin@example.com`): builds the category tree, creates tags, and adds products with a price, stock, a category and tags. Orders are visible there but read-only.
2. **A shopper browses the storefront** at `/`. Anyone can search from the header and filter from the sidebar by category (including subcategories), tags (all or any), price range and stock, then press **Apply** (or **Reset**). Every filter lives in the URL, so results can be bookmarked and paginated. Each card shows the product's picture (or a placeholder), its price and stock, a **Details** link and, for products in stock, a **Buy** button. Visitors who are not logged in see these too.
3. **Details** opens the product page at `/products/<slug>/` with the picture, the full description, the category path, tags, price and stock, plus **Buy** (when in stock) and, for logged-in users, **♡ Favourite**. Out-of-stock products have a page too, without Buy.
4. **Visitors who click Buy** are sent to the login page and, after logging in or signing up, come back to the page they were on. Nothing is bought until they click Buy again. Anyone can **create an account** at `/accounts/signup/` (linked from the login page) with an email address and a password entered twice; the email becomes the username, and the new account is a regular shopper with no admin access. Logged-in users also get **♡ Favourite** on every card and **Only my favourites** in the sidebar. Favourites are toggled from any card or product page and listed under **My favourites**, including products that are now out of stock.
5. **Buy** places a one-unit order straight away and shows a confirmation, or an "out of stock" message if someone bought the last unit first. Stock drops immediately.
6. **My orders** lists past orders, newest first, with the prices that were paid.
7. **API clients** use the same catalog through `/api/`: read the products with the storefront's filter parameters, get a JWT at `/api/auth/token/`, then manage favourites and place multi-item orders. Everything can be tried in Swagger UI at `/api/docs/` (see [API](#api)).

### Development workflow

```bash
uv sync                                                          # install dependencies into .venv
uv run --env-file .env python manage.py test                     # run the test suite (~270 tests)
uv run --env-file .env python manage.py makemigrations --check   # confirm models and migrations agree
uv run --env-file .env python manage.py spectacular --validate --fail-on-warn --file /dev/null   # check the OpenAPI schema
```

Code layout (`catalog/` is the only app):

| File | What it holds |
|---|---|
| `models.py` | `Category`, `Tag`, `Product`, `Favorite`, `Order`, `OrderItem`, the Unix-timestamp base model, and the category validation rules |
| `querysets.py` | `ProductQuerySet`: `search`, `in_category`, `with_tags`, `price_between`, `in_stock`, `favorites_of`, `with_is_favorite`, `for_listing` |
| `filters.py` | `ProductFilterSet`, the filter definition shared by the storefront and the API |
| `category_tree.py`, `signals.py` | The cached category tree and its invalidation |
| `services.py` | `place_order()` and `OutOfStock` |
| `views.py`, `urls.py`, `templates/` | The storefront |
| `accounts.py` | Sign-up and the email login form |
| `api/` | Serializers, viewsets and API routes |
| `admin.py` | Admin configuration |
| `fixtures/` | Demo data |
| `tests/` | One test module per capability |

All commands load settings from `.env` through `uv run --env-file .env`. Without it Django refuses to start when `SECRET_KEY` is missing (debug mode is off by default).

The project was planned with [OpenSpec](https://github.com/Fission-AI/OpenSpec). Changes go through propose → apply → archive (`/opsx:propose`, `/opsx:apply`, `/opsx:archive`):

```
openspec/
  config.yaml                                   project-level OpenSpec settings
  specs/<capability>/spec.md                    living specs: the current required behaviour (10 capabilities)
  changes/archive/2026-11-22-product-catalog/   the archived change that built this project
    proposal.md                                 why and what
    design.md                                   technical decisions (D1-D13)
    specs/<capability>/spec.md                  the delta specs it added
    tasks.md                                    the implementation checklist, with notes
```

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync
cp .env.example .env
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py loaddata catalog demo_users
uv run --env-file .env python manage.py runserver
```

Open http://127.0.0.1:8000/ for the storefront and http://127.0.0.1:8000/admin/ for the admin.

### Demo data

Two fixtures live in `catalog/fixtures/`. Load them **in this order**, because the users fixture refers to catalog products through the first shopper's favourites:

1. `catalog.json`: **7 categories** in a three-level tree (Books; Electronics > Audio > Headphones and Speakers; Electronics > Computers & Phones; Home & Outdoors), 12 tags and **25 products** (2 of them out of stock), spread over three storefront pages. 24 products have a picture; "Starfall Chronicles" has none, so it shows the placeholder. It was exported with `dumpdata catalog.category catalog.tag catalog.product --indent 2` and contains no user accounts.
2. `demo_users.json`: three accounts and the first shopper's favourites. Passwords are stored only as hashes.

| User (email) | Password | Access |
|---|---|---|
| `admin@example.com` | `demo-admin-123` | Superuser: the admin at `/admin/` and the storefront |
| `shopper@example.com` | `demo-shopper-123` | Storefront and API only (no admin), with 4 favourites |
| `shopper2@example.com` | `demo-shopper2-123` | Storefront and API only (no admin), with no favourites |

**Pictures need internet access.** Each `image_url` points at a freely licensed photo on [Wikimedia Commons](https://commons.wikimedia.org/) (960px thumbnails on `upload.wikimedia.org`). Offline, or if a link breaks, cards and product pages show the placeholder. The photos are only illustrations: the products are fictional, and each file keeps its own Commons licence.

To start again from clean demo data, for example after pulling a new version of the fixtures, reload everything (this deletes all data in the database, including orders and accounts you created):

```bash
uv run --env-file .env python manage.py flush --no-input
uv run --env-file .env python manage.py loaddata catalog demo_users
```

> **Warning:** never load `demo_users` in production. Its passwords are public in this README.

## Assumptions

### Category tree

- Categories form a tree through a `parent` field (empty = top level). Names are unique across the whole catalog, not just among siblings.
- Each category holds **either products or subcategories**, never both. The admin shows this as one "Holds" choice; the database stores two flags with a check constraint that exactly one is set.
- The maximum depth is `CATALOG_MAX_CATEGORY_DEPTH` (default **3**, counting the top level as 1). Categories at the deepest level must hold products.
- Saving a category is validated against the database: no loops (a category under itself or its descendant), no level beyond the maximum (also for subcategories when a whole branch is moved), the parent must hold subcategories, and the kind can't change while the category still has products or children.
- Categories with products or children can't be deleted (`PROTECT`); the admin lists what blocks the deletion.
- Filtering by a category includes every category below it.
- The tree is cached in memory for an hour and cleared as soon as a category change commits.
- **Lowering `CATALOG_MAX_CATEGORY_DEPTH`** doesn't touch existing categories. Ones that are now too deep keep working but fail validation the next time they're saved in the admin.

### Accounts

- **Sign-up** (`/accounts/signup/`) takes an email address and a password twice. The password must pass Django's validators (at least 8 characters, not too common, not all digits, not too similar to the email). There is no email verification and no password reset.
- **The email is the username**, stored in lower case. A second sign-up with the same address in any letter case is rejected.
- **Login** (`/accounts/login/`) labels the first field "Email" and matches it ignoring letter case. The admin login and the API token endpoint (`/api/auth/token/`) still match the username exactly, so use the lower-case email there.
- Both pages keep the `next` target, so a visitor who clicked Buy lands back on the same page. Only targets on this site are accepted.

### Search and filters

The storefront and the API share one filter definition (`catalog/filters.py`), so the same query string gives the same products in both. All active filters combine with AND.

| Parameter | Meaning |
|---|---|
| `q` | Search text. It's split into words (up to 10) and **every word** must appear in the name or the description. |
| `category` | One category id. It **includes every category below it**. |
| `tags` | Tag ids, repeated (`tags=1&tags=4`). |
| `match` | `all` (default): products must have every selected tag. `any`: at least one. Each product appears once. |
| `price_min`, `price_max` | Inclusive bounds **in cents**. A minimum above the maximum is an error. |
| `include_out_of_stock` | `true`/`1` to include products with zero stock. They're **hidden by default**. |
| `favorites` | `true` to show only your favourites. Ignored on the storefront for anonymous visitors; the API answers 401. |

- Matching uses `icontains`, so it finds substrings ("art" matches "smartphone"). On SQLite it's case-insensitive only for ASCII letters.
- An unknown category or tag, a non-number, or an inverted price range shows a form error on the storefront and returns 400 from the API.
- Results are ordered by name, and pagination keeps the filters.

### Favourites and checkout

- Favourites are private to each user. Adding one twice or removing one that isn't there both succeed without changes. Deleting a user or a product removes the related favourites.
- **Buy** on the storefront orders one unit. The API accepts orders with several items.
- **All-or-nothing:** if any item lacks stock, no order is created and no stock changes. The API answers `409` and lists every product that was short.
- **No overselling:** each item's stock is decremented with one conditional `UPDATE ... WHERE items_available >= quantity` inside a transaction (`catalog/services.py`). Two buyers racing for the last unit get one success and one "out of stock"; a threaded test checks this.
- **Prices are copied at purchase** into each order item, so later repricing never changes past orders or their totals.
- Orders are view-only in the admin. Products that were ordered and users with orders can't be deleted.
- **SQLite concurrency:** SQLite allows one writer at a time. Write transactions start with `BEGIN IMMEDIATE` and wait up to 20 seconds for the lock, which avoids "database is locked" errors under a demo-sized load. The same design works unchanged on PostgreSQL.

### Products, prices and timestamps

- Product and tag names are unique. A product has exactly one category (one that holds products) and any number of tags.
- **Slug:** every product has a unique URL slug (lower-case letters, digits and hyphens). It is generated from the name when the product is created (`aurora-anc-headphones`, with `-2`, `-3`… added on a clash) and **does not change when the product is renamed**. It can be edited in the admin, and the product page lives at `/products/<slug>/`. The old id-based product URLs never existed, so nothing redirects.
- **Picture:** `image_url` is optional, holds one `http` or `https` address and is never downloaded or stored by the server. The browser loads it directly. Deleting a tag removes it from products; the products stay.
- **Prices are integer cents** in a single currency (`price_cents = 4900` shows as `$49.00`), which avoids floating-point rounding. Price filters in the URL and the API are in cents too.
- **Stock** (`items_available`) can never go below zero; the database enforces it with a check constraint.
- **Timestamps** (`created_at`, `updated_at`) on every catalog table are **whole Unix seconds** (UTC), shown as readable dates in the admin. Not covered: the automatic product–tag link table and tables owned by Django or libraries (users, sessions, token blacklist), which have their own date fields.

## API

The JSON API lives under `/api/`. Interactive docs (Swagger UI) are at **`/api/docs/`** and the OpenAPI 3 schema is at **`/api/schema/`**.

| Endpoint | Methods | Auth | Notes |
|---|---|---|---|
| `/api/products/` | GET | none | Paginated (20 per page). Each product includes `slug` and `image_url` (`""` when it has no picture). Takes every storefront filter parameter (see [Search and filters](#search-and-filters)). `favorites=true` requires auth (401 otherwise). |
| `/api/products/{id}/` | GET | none | Includes `is_favorite` when authenticated. |
| `/api/categories/`, `/api/categories/{id}/` | GET | none | Parent id, full `path`, `has_products` / `has_subcategories`. |
| `/api/tags/`, `/api/tags/{id}/` | GET | none | |
| `/api/favorites/` | GET, POST | required | POST `{"product": 7}` returns 201, or 200 if it was already a favourite. Unknown product: 400. |
| `/api/favorites/{product_id}/` | DELETE | required | 204 whether or not it was a favourite. |
| `/api/orders/` | GET, POST | required | POST `{"items": [{"product": 7, "quantity": 2}]}` returns 201 with items and total; 400 for bad input; **409** `{"out_of_stock": [ids]}` when stock is short. |
| `/api/orders/{id}/` | GET | required | Other users' orders return 404. |
| `/api/auth/token/` | POST | none | Username and password in, `access` and `refresh` tokens out. |
| `/api/auth/token/refresh/` | POST | none | Refresh token in, new pair out (the old refresh token stops working). |
| `/api/auth/logout/` | POST | none | Revokes the given refresh token. |

The catalog endpoints are read-only: write methods return 405. Errors are JSON with the usual status codes (400, 401, 404, 405, 409), never stack traces.

### Authentication

- **Browser:** pages and same-site API calls (including Swagger UI) use the login session. Session-authenticated writes need a CSRF token.
- **API clients:** use JSON Web Tokens. Access tokens last **15 minutes** and refresh tokens **1 day** (change with `JWT_ACCESS_MINUTES` / `JWT_REFRESH_MINUTES`). Refreshing rotates the refresh token and blacklists the old one; logout blacklists it too. Access tokens already issued stay valid until they expire.

With curl (the demo shopper, server on port 8000):

```bash
# 1. Get a token pair
curl -s -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "shopper@example.com", "password": "demo-shopper-123"}'

# 2. Call the API with the access token
ACCESS=<access token from step 1>
curl -s http://127.0.0.1:8000/api/favorites/ -H "Authorization: Bearer $ACCESS"
curl -s -X POST http://127.0.0.1:8000/api/orders/ -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" -d '{"items": [{"product": 2, "quantity": 1}]}'

# 3. Get a new pair when the access token expires
curl -s -X POST http://127.0.0.1:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh": "<refresh token>"}'

# 4. Log out (revokes the refresh token)
curl -s -X POST http://127.0.0.1:8000/api/auth/logout/ \
  -H "Content-Type: application/json" -d '{"refresh": "<refresh token>"}'
```

In **Swagger UI** (`/api/docs/`): run `POST /api/auth/token/` with "Try it out", copy the `access` value, click **Authorize**, paste it into `jwtAuth`, and the protected endpoints will work. If you're logged in to the site in the same browser, Swagger also works through the session.

## Configuration

All settings that vary between deployments come from environment variables. `.env.example` has safe development values; load them with `uv run --env-file .env ...`.

| Variable | Default | Purpose |
|---|---|---|
| `DEBUG` | off | `1` for development. Anything unset means production mode. |
| `SECRET_KEY` | none | Required when `DEBUG` is off: startup fails without it. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` in debug, else empty | Comma-separated host names. |
| `CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins (with scheme) trusted for form posts. |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated browser origins allowed to call `/api/`. Empty means no cross-origin access. |
| `JWT_ACCESS_MINUTES` | `15` | Access token lifetime. |
| `JWT_REFRESH_MINUTES` | `1440` | Refresh token lifetime (1 day). |
| `CACHE_BACKEND` | `django.core.cache.backends.locmem.LocMemCache` | Cache for the category tree. |
| `CACHE_LOCATION` | `catalog` | Cache location (for example a Redis URL with the Redis backend). |
| `CATALOG_MAX_CATEGORY_DEPTH` | `3` | Maximum category tree depth, counting the top level. |
| `SQLITE_PATH` | `db.sqlite3` | Database file. |
| `SQLITE_TEST_PATH` | `test_db.sqlite3` | Test database file (a file, so the concurrency test uses real locks). |
| `SECURE_SSL_REDIRECT` | on when `DEBUG` is off | Redirect HTTP to HTTPS. |
| `SECURE_HSTS_SECONDS` | one year when `DEBUG` is off | HSTS max-age. |
| `TRUST_X_FORWARDED_PROTO` | off | Trust `X-Forwarded-Proto` from a TLS-terminating proxy. |

### Security notes

- **CSRF:** every state-changing form (Buy, favourites, login, logout, admin) carries a CSRF token; requests without one get 403. State-changing views accept only POST (GET returns 405).
- **CORS** (django-cors-headers) applies only to `/api/` paths and only to origins in `CORS_ALLOWED_ORIGINS`. It never allows credentials, so cross-origin clients must use bearer tokens, not cookies. Allowed methods are GET, HEAD, OPTIONS, POST and DELETE; allowed headers are `Authorization` and `Content-Type`.
- **Clickjacking:** every page is sent with `X-Frame-Options: DENY`, and with `X-Content-Type-Options: nosniff`.
- **Production mode** (`DEBUG` off) turns on HTTPS redirect, secure cookies and HSTS. This passes Django's deployment check:

  ```bash
  DEBUG=0 SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(60))')" ALLOWED_HOSTS=shop.example.com uv run python manage.py check --deploy
  ```

  A test runs the same check.
- **Redirects** taken from `next` parameters are limited to this site; anything else goes to the home page.
- Tokens are never rendered into storefront pages and no token is committed to the repository.

## Known limitations

- **One process only.** The category tree is cached in each process's memory (`LocMemCache`). With several workers, a category edit clears the cache only in the worker that handled it; the others serve the old tree for up to an hour. Point `CACHE_BACKEND` at a shared cache (Redis or Memcached) before running more than one worker.
- **Writes that skip signals.** `QuerySet.update()` or `bulk_create()` on categories don't clear the cache. The code never does this; the one-hour timeout limits how long a stale tree could last.
- **Fixtures and the shell skip validation.** `loaddata` and direct ORM writes bypass the category rules in `clean()`. The admin is the only write path, and a test runs full validation over the fixtures.
- **SQLite allows one writer at a time.** Fine for a demo; checkout waits up to 20 seconds for the write lock. Use PostgreSQL for real traffic (no code changes needed).
- **Search is substring matching** (`icontains`): "art" matches "smartphone", there's no ranking, and SQLite only folds case for ASCII letters.
- **Access tokens can't be revoked** before they expire (15 minutes). Refresh tokens are rotated and blacklisted on logout.
- **Swagger UI loads its JavaScript and CSS from a CDN.**
- **Lowering `CATALOG_MAX_CATEGORY_DEPTH`** leaves existing deeper categories in place without a warning; they fail validation on their next save.
- Timestamps don't cover the automatic product–tag table or tables owned by Django and libraries.
- **Pictures are hotlinked.** The demo pictures load from Wikimedia Commons, so they need internet access and can disappear; the placeholder takes over.
- **No email verification or password reset.** Sign-up accepts any well-formed email address, and there is no rate limiting on sign-up or login.
- There's no cart, payment, order status, stock reservation, i18n or multi-currency support.

## Future work

- **Full-text search** with SQLite FTS5 (or PostgreSQL search) for ranking, stemming and whole-word matches.
- **A shopping cart**, so the storefront can place multi-item orders like the API does.
- **A shared cache backend** (Redis) to run several workers.
- **Content-Security-Policy** headers and **rate limiting** (especially on login and token endpoints).
- Self-hosted Swagger UI assets (`drf-spectacular-sidecar`).
