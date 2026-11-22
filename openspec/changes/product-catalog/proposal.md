# Proposal

## Why

The take-home assignment (`ASSIGNMENT.md`) asks for a Django project that models products, categories and tags. Data is entered through the Django admin, and an HTML page lets visitors search by description and filter by category and tags, with the filters combinable. Reviewers grade correct relationships, effective querysets, code quality, documentation and completeness. The repository has only a PyCharm sample script today, so everything has to be built from scratch.

During exploration the scope grew beyond the brief. It now covers a nested category tree, stock and prices, favourites, one-click checkout, a JSON API with OpenAPI docs, JWT authentication, caching and security hardening. This proposal records the agreed scope so the build stays focused. The assignment's core comes first and the extensions follow.

## What Changes

- New Django project (`config/`) with one app (`catalog/`), managed with uv and `pyproject.toml`, using SQLite. The PyCharm sample `main.py` is removed.
- **Category tree**: a self-referencing `parent` field (NULL = top level), built top-down. Maximum depth is set by `CATALOG_MAX_CATEGORY_DEPTH` (default 3, counting the top level). Each category holds either products or subcategories, never both, as two flags with exactly one true. Names are unique across the catalog. Loops, depth and flag rules are validated on save.
- **Products**: unique name, description, price in integer cents, `items_available` stock (≥ 0), one category (only one that holds products), and many tags. **Tags** have unique names. Every catalog table records `created_at`/`updated_at` as Unix seconds.
- **Search and filtering**: search across name and description where every word must match (`icontains`); one category per query, including all of its descendant categories; tags matched ALL (default) or ANY; price range; out-of-stock products hidden by default; an "only favourites" filter. All of it runs through one shared filter definition used by both the HTML page and the API.
- **Storefront** (Django templates): a header search bar and user menu; a sidebar that is a single GET form (category radio tree, price sliders, tags with ALL/ANY, stock and favourites toggles, Apply/Reset); product cards with price, stock, a favourite button and a Buy button; "My favourites" and "My orders" pages; login and logout.
- **Favourites**: logged-in users add and remove favourite products from the storefront and the API.
- **Checkout**: one-click Buy on the storefront creates an order with one item. The API accepts orders with several items. `Order` + `OrderItem` tables store copies of the prices paid. Stock is decremented atomically, the whole order fails if any item is short, and the API returns 409 listing every out-of-stock product.
- **JSON API** (DRF): read-only catalog endpoints (products, categories, tags) plus user-scoped favourites and orders endpoints. OpenAPI 3 schema and Swagger UI via drf-spectacular.
- **Authentication**: session login for browser pages, and JWT for API clients (simplejwt, with refresh rotation and a blacklist so logout revokes tokens).
- **Security**: CSRF on every session-authenticated write. CORS restricted to an allowlist from the environment, on the API only, without credentials. `SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` from the environment. `manage.py check --deploy` passes with production settings.
- **Caching**: the category tree is cached in memory (`LocMemCache`, switchable through the environment). The cache is cleared after the transaction commits whenever a category is saved or deleted, with a 1-hour timeout as a safety net.
- **Demo data**: a catalog fixture (≥ 5 categories, ≥ 10 tags, ≥ 20 products, entered through the admin and then dumped) and a users fixture (an admin superuser and a shopper with some favourites).
- **README** with a project description, a features list, the workflow (user flow, and the development flow with uv, tests and OpenSpec), setup, assumptions, demo credentials and known limitations. It is kept current as each feature group lands. **Future to-dos**: full-text search (SQLite FTS5), a shopping cart, and a shared cache backend for running with several workers.

## Capabilities

### New Capabilities

- `category-hierarchy`: the category tree (parent field, depth limit, products-or-subcategories flags, unique names, loop/depth validation) and cached tree reads with invalidation.
- `catalog-data`: products and tags (unique names, price in cents, stock, Unix timestamps, relationships to categories and tags), managed through the Django admin.
- `product-search`: search, category/tag/price/stock/favourites filters and how they combine, shared by the storefront and the API.
- `storefront`: the server-rendered shop pages (listing with sidebar filter form, product cards, favourites and orders pages, login/logout).
- `favorites`: per-user favourite products, managed from the storefront and the API.
- `checkout`: one-click and API order placement, stock control, and the order history.
- `catalog-api`: the JSON API (read-only catalog, user-scoped favourites and orders) and its OpenAPI/Swagger documentation.
- `api-auth`: session authentication for browser pages and JWT issue/refresh/logout for API clients.
- `web-security`: CSRF, CORS and configuration from the environment.
- `demo-data`: fixtures that seed the catalog and the two demo users.

### Modified Capabilities

None. There are no existing specs.

## Impact

- **Code**: new `config/` (settings, urls), `catalog/` (models, admin, querysets, filters, services, views, serializers, templates, migrations, tests, fixtures), `pyproject.toml`, `uv.lock`, `README.md` and `.gitignore`. `main.py` is removed.
- **Dependencies**: Django (5.2 LTS), djangorestframework, drf-spectacular, django-filter, django-cors-headers, djangorestframework-simplejwt.
- **Runtime**: SQLite file database and an in-memory cache, so no external services are needed. Only one process is supported until there is a shared cache backend.
- **Scope risk**: this is much more than the assignment's "a few hours". The tasks are ordered so the required core (models, admin, search/filter page, README) is complete and usable before the extensions start.
