# Design

## Context

The project starts empty: only `ASSIGNMENT.md` and a PyCharm sample `main.py`. See `proposal.md` for the motivation and scope, and `specs/` for the required behaviour. Constraints that shape the approach:

- Reviewers will clone a public repository and run it locally, so setup must need no external services. That means SQLite, an in-memory cache and `uv sync`.
- The assignment grades queryset skill, so query logic must be visible, centralised and tested, not hidden in views or frameworks.
- All catalog writes go through the Django admin. The only end-user writes are favourites and orders.

## Goals / Non-Goals

**Goals:**

- One place for each rule: filtering in a queryset plus a FilterSet, order placement in a service function, category rules in model validation and constraints.
- A fixed number of SQL queries per product page, whatever the page size.
- Correct stock handling when orders arrive at the same time.
- Build order so the assignment's core works before the extensions are added (see `tasks.md`).

**Non-Goals:**

- Running with several worker processes (the cache is per-process; see Risks).
- Full-text search, a shopping cart, payments, order status workflow, a JS front-end framework, i18n or multi-currency.
- Content-Security-Policy and rate limiting.

## Decisions

### D1. Project layout: one `catalog` app

```
config/            settings.py, urls.py, wsgi.py, asgi.py
catalog/
  models.py        Category, Tag, Product, Favorite, Order, OrderItem
  querysets.py     ProductQuerySet (search, in_category, with_tags, ...)
  category_tree.py CategoryTree (cached tree: ordered nodes, paths, descendants)
  filters.py       ProductFilterSet (shared by storefront + API)
  services.py      place_order(), OutOfStock
  signals.py       cache invalidation
  admin.py
  views.py         storefront views
  api/             serializers.py, views.py, urls.py
  templates/catalog/ , templates/registration/
  templatetags/money.py
  fixtures/        catalog.json, demo_users.json
  tests/
```

*Alternative:* separate apps (`catalog`, `shop`, `accounts`). This was rejected because the domain is small and tightly coupled; separate apps would add cross-app imports without making the boundaries clearer.

### D2. Category tree: a parent field, two kind flags, validation in `clean()`

- `parent = ForeignKey("self", null=True, blank=True, on_delete=PROTECT, related_name="children")`.
- `has_products` / `has_subcategories` booleans with a `CheckConstraint` requiring exactly one to be True. The admin form shows this as a single radio choice ("Holds: products / subcategories") that sets both flags.
- `name` unique. `CATALOG_MAX_CATEGORY_DEPTH` (default 3, counting the top level) lives in settings.
- `Category.clean()` loads all `(id, parent_id)` pairs **from the database** (one query, not the cache) and checks loops, its own depth, the depth of its subtree when it moves, the parent's kind, the deepest-level rule, and kind changes against `products.exists()` / `children.exists()`.

*Alternatives:* django-treebeard or django-mptt, which were rejected as an extra dependency and more complexity than a 3-level tree needs. A single `is_leaf` flag, or deriving the kind from whether children exist, was considered and rejected by the user in favour of explicit flags. Rules that span rows can't be database constraints, which is why they live in `clean()`. This is safe because the admin is the only write path. Fixtures skip `clean()`, so a test checks them separately.

### D3. Cached `CategoryTree` drives navigation, labels and the category filter

`get_category_tree()` returns an immutable object built from one query, `values_list("id", "parent_id", "name", "has_products", "has_subcategories")`. It provides:
- the nodes in depth-first order with their depth (for the sidebar radio tree),
- `path(id)` → "Electronics > Audio > Headphones",
- `descendant_ids(id)` → the set of ids in that subtree, including the category itself.

It's stored with `cache.get_or_set(KEY, build, timeout=3600)`. `post_save`/`post_delete` receivers on `Category` call `transaction.on_commit(lambda: cache.delete(KEY))`, so a concurrent request can't re-cache the old tree before the commit lands.

The category filter becomes `filter(category_id__in=tree.descendant_ids(c))`: one plain `IN` on the product table, with no joins.

*Alternatives:* chained `category__parent__parent` lookups built from MAX_DEPTH (one SQL statement, no cache), which were superseded once caching was in scope. A recursive CTE, rejected because it needs raw SQL.

### D4. One `ProductFilterSet` shared by the storefront and the API

A django-filter `FilterSet` defines all parameters, and each filter method calls a `ProductQuerySet` method:

| Param | Type | Method |
|---|---|---|
| `q` | text | `.search(q)`: split into words (at most 10), each word `Q(name__icontains) \| Q(description__icontains)`, ANDed together |
| `category` | single choice (tree radio widget) | `.in_category(ids)` |
| `tags` | multiple choice | `.with_tags(ids, match)` |
| `match` | `all` (default) / `any` | used by `tags` |
| `price_min`, `price_max` | int, cents | `price_cents__gte/__lte`; the form checks min ≤ max |
| `include_out_of_stock` | bool | absent → `.in_stock()` (`items_available__gt=0`) |
| `favorites` | bool | `.favorites_of(user)` |

`with_tags` uses a subquery on the many-to-many through table, so the main query never joins tags and never needs `.distinct()`:

```python
through = Product.tags.through.objects.filter(tag_id__in=ids)
if match == "all":
    through = through.values("product_id").annotate(n=Count("tag_id")).filter(n=len(ids))
return self.filter(id__in=through.values("product_id"))
```

`len(ids)` is reliable because the multiple-choice field returns distinct pks.

Listing adds `select_related("category")`, `prefetch_related("tags")` and, for logged-in users, `annotate(is_favorite=Exists(Favorite...OuterRef("pk")))`. Category paths come from the cached tree. The query count stays fixed (spec: product-search, bounded query count). Default ordering is by `name`.

Price slider bounds come from one `aggregate(Min, Max)` query over all products. The parameters are in cents. The sliders step by 100, and a few lines of inline JS update their dollar labels.

Anonymous users with `favorites=true` have the filter ignored on the storefront (the control is hidden). The API view checks for it and raises `NotAuthenticated` (401) before filtering, which keeps DRF out of the FilterSet.

*Alternatives:* a plain Django `Form` plus hand-written schema parameters, rejected because the parameters would be declared twice and drift apart. Joining tags with `.distinct()`, which works but needs `.distinct()` for correctness and complicates combining with other queries.

### D5. Storefront: class-based views and one GET form

- `ProductListView` (ListView + FilterSet, 12 items per page). Its form renders the header search bar and the sidebar as **one** `<form method="get">`, using the HTML `form=` attribute so the header input belongs to the sidebar form.
- The category radio tree is a custom widget template that indents each choice by its depth from `CategoryTree`, with an "All" option first.
- POST-only views for favourite add/remove and Buy, each with `@login_required`, `require_POST`, CSRF, a success/error message via the `messages` framework, and a redirect to a `next` value checked with `url_has_allowed_host_and_scheme`.
- `MyFavoritesView` (which includes out-of-stock products) and `MyOrdersView` (`prefetch_related("items__product")`, newest first).
- Login and logout use `django.contrib.auth` views and templates. Logout is POST-only, as Django ≥ 5 requires.

*Alternative:* category links built with `{% querystring %}`, rejected by the user in favour of a single form (option a).

### D6. Timestamps as Unix seconds

Every catalog model (Category, Tag, Product, Favorite, Order, OrderItem) inherits from the abstract `TimestampedModel`. It has `created_at` and `updated_at = PositiveBigIntegerField(default=unix_now, editable=False)`, and `save()` sets `updated_at` to the current time. Code paths that use `QuerySet.update()` (the checkout stock decrement) set `updated_at` explicitly, and `bulk_create` relies on the field defaults. Not covered: the automatic product–tag table (it would need an explicit through model) and tables owned by Django or other libraries (`auth_user` already has `date_joined`/`last_login`; the token blacklist tables have their own timestamps). The admin and the API show readable dates through a helper. BigInteger avoids the 2038 overflow on backends other than SQLite.

*Alternative:* `DateTimeField(auto_now…)`. The user explicitly chose Unix seconds. What's lost: `__date`-style lookups, `date_hierarchy` and automatic time-zone rendering.

### D7. Checkout: a conditional UPDATE in one transaction

`place_order(user, items)` in `services.py`, wrapped in `@transaction.atomic`:

1. Sort the items by product id, so locks are always taken in the same order on backends with row locks.
2. For each item, run `Product.objects.filter(pk=…, items_available__gte=qty).update(items_available=F(...) - qty, updated_at=now)`. If it returns 0, record the product as out of stock.
3. If any product is out of stock, raise `OutOfStock(product_ids)`. The transaction rolls back every decrement.
4. Otherwise read the current prices and create `Order` (with `total_cents`) and `OrderItem`s via `bulk_create`, copying the prices.

The API maps `OutOfStock` to 409 `{"out_of_stock": [ids]}`. The storefront turns it into an error message. The database `CHECK items_available >= 0` is a backstop. The SQLite connection uses `OPTIONS = {"transaction_mode": "IMMEDIATE", "timeout": 20}` (Django ≥ 5.1), so writing transactions take the write lock at BEGIN. That avoids "database is locked" failures when a read lock has to be upgraded under concurrency.

*Alternatives:* `select_for_update()` then check and save. SQLite ignores the row lock, and it needs more round trips. Read-check-write in Python has a race condition.

### D8. API: DRF viewsets, secure by default

- Default permission `IsAuthenticated`. Catalog viewsets (`ReadOnlyModelViewSet`) override it with `AllowAny`, so unknown write methods return 405.
- `FavoriteViewSet` supports list, create and destroy, uses `lookup_field="product_id"`, and builds its queryset from `request.user`. `OrderViewSet` supports list, retrieve and create, with the queryset also scoped to `request.user`, so other users' objects return 404.
- Separate read and write serializers for orders. The write serializer validates the item list: not empty, quantity ≥ 1, product exists, no duplicates.
- `PageNumberPagination` (page size 20). DRF's default JSON error format, plus a custom `APIException` for 409.

### D9. Authentication: JWT first, then session

`DEFAULT_AUTHENTICATION_CLASSES = [JWTAuthentication, SessionAuthentication]`. JWT comes first so unauthenticated responses are **401** with `WWW-Authenticate: Bearer`, not 403. The simplejwt settings are: access 15 min, refresh 1 day (overridable through env), `ROTATE_REFRESH_TOKENS` and `BLACKLIST_AFTER_ROTATION` with the `token_blacklist` app. The routes are `/api/auth/token/`, `/api/auth/token/refresh/`, and `/api/auth/logout/` (simplejwt's blacklist view). Session-authenticated API writes are CSRF-checked by DRF.

*Alternatives:* DRF Token or Basic auth. The user chose JWT.

### D10. OpenAPI: drf-spectacular

`/api/schema/` serves the schema and `/api/docs/` serves Swagger UI. The extensions bundled with drf-spectacular document the django-filter parameters and the JWT bearer scheme automatically. `@extend_schema` covers the 409 response and the favourites lookup by product id.

### D11. Settings from the environment, no extra library

Small `env_str/env_bool/env_list/env_int` helpers in `settings.py`. With `DEBUG` off, the security settings are switched on: `SECURE_SSL_REDIRECT`, secure cookies, HSTS, `SECURE_CONTENT_TYPE_NOSNIFF` and `X_FRAME_OPTIONS="DENY"`. A missing `SECRET_KEY` raises `ImproperlyConfigured`. A committed `.env.example` holds safe development values, and `uv run --env-file .env …` loads them. CORS uses django-cors-headers with `CORS_ALLOWED_ORIGINS` from env, `CORS_URLS_REGEX=r"^/api/.*$"`, `CORS_ALLOW_CREDENTIALS=False`, and `CORS_ALLOW_METHODS` limited to GET, HEAD, OPTIONS, POST and DELETE. The cache backend and location come from `CACHE_BACKEND`/`CACHE_LOCATION` (default LocMem).

*Alternative:* django-environ or python-dotenv. One more dependency for about 20 lines of helpers.

### D12. Fixtures

The catalog data is typed into the admin, then exported with `dumpdata catalog.category catalog.tag catalog.product --indent 2`. `demo_users.json` contains `auth.user` records with `make_password` hashes, plus `catalog.favorite` rows. It's loaded after the catalog. A test loads both fixtures and runs `full_clean()` on every record to cover what `loaddata` skips.

### D13. Testing strategy

Django `TestCase` with one test module per capability. The query-count tests use `assertNumQueries`. Cache-invalidation tests use `captureOnCommitCallbacks`. The concurrency test for the last unit runs sequential competing calls in `TestCase`, plus a threaded `TransactionTestCase` against a file-based SQLite test database. It falls back to a skip with an explanation if SQLite locking makes it flaky.

## Risks / Trade-offs

- [The per-process LocMem cache goes stale when running several workers] → document single-process use; the backend can be switched through env; a shared backend is a future to-do.
- [`QuerySet.update()`/`bulk_create()` on categories skip the signals that clear the cache] → the code never does this for categories; a 1-hour timeout limits staleness; a comment marks it.
- [Fixtures and the shell bypass `clean()`, so cross-row category rules could be broken] → a fixture validation test; the admin is the only write path.
- [SQLite write concurrency is limited (one writer at a time)] → `IMMEDIATE` transactions plus a busy timeout; acceptable for a demo; the conditional UPDATE design carries over to Postgres unchanged.
- [`icontains` is case-insensitive only for ASCII on SQLite and matches substrings, e.g. "art" matches "smartphone"] → documented; FTS5 is a future to-do.
- [Access tokens can't be revoked before they expire] → 15-minute lifetime; refresh tokens are rotated and blacklisted.
- [Swagger UI loads its assets from a CDN] → acceptable for a demo; drf-spectacular-sidecar can self-host them later.
- [Changing `CATALOG_MAX_CATEGORY_DEPTH` to a lower value leaves existing deeper categories invalid without warning] → documented; validation catches it on their next save.
- [The scope far exceeds the assignment's "few hours"] → tasks are ordered so the core is complete first.

## Migration Plan

This is a greenfield project with no existing data. Setup for reviewers:

```bash
uv sync
cp .env.example .env
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py loaddata catalog demo_users
uv run --env-file .env python manage.py runserver
```

Rollback is irrelevant, since nothing is deployed.

## Open Questions

- Exact Django patch version and the `requires-python` range. Use the newest 5.2 LTS patch that supports the local Python (3.14); if it doesn't, pin Python 3.13 via `.python-version`. Checked during setup; no spec impact.
- Page sizes (12 for the storefront, 20 for the API) can be tuned later.
