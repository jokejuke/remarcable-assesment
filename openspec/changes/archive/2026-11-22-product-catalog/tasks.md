# Tasks

> Groups 1–6 deliver the assignment's required core (models, admin, search/filter page, fixtures, README). Groups 7–12 are the agreed extensions. Each group ends in a working, tested state, with its README section written and its items ticked in the README "Features" checklist.

## 1. Project setup

- [x] 1.1 Remove the PyCharm sample `main.py`. Create `pyproject.toml` with uv (Django 5.2 LTS latest patch; pick `requires-python` from its supported versions, adding `.python-version` 3.13 if 3.14 isn't supported). Verify with `uv sync`, which creates `uv.lock` and a working venv.
- [x] 1.2 Create the Django project `config/` and app `catalog/` as laid out in design D1. Verify `uv run python manage.py check` passes.
- [x] 1.3 Add `.gitignore` (venv, `db.sqlite3`, `.env`, `__pycache__`, `.idea/`) and `.env.example` with safe development values. Verify `git check-ignore .env db.sqlite3` matches once the repository exists.
- [x] 1.4 Implement env helpers and settings per D11: `SECRET_KEY`, `DEBUG` defaulting to off, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, cache backend, SQLite `transaction_mode=IMMEDIATE` + `timeout`, and security settings switched on when `DEBUG` is off. Verify with tests: missing `SECRET_KEY` with `DEBUG` off raises `ImproperlyConfigured`; an unset `DEBUG` means off.
- [x] 1.5 Create `README.md` with these sections, in this order: **Project description** (what it is, the assignment context, the tech stack); **Features** (a checklist, ticked off as each group lands); **Workflow**, covering (a) the user workflow (admin manages the catalog → shopper browses and filters → favourites → Buy → My orders, plus API use through Swagger and JWT) and (b) the development workflow (uv commands, running tests, OpenSpec propose/apply/archive, the `openspec/` layout); **Setup** (uv install link, the commands from design "Migration Plan"); then placeholders for Assumptions, API, Configuration, Known limitations and Future work. Verify the setup commands run as written on a fresh clone of the working tree.

## 2. Category hierarchy

- [x] 2.1 Add the `Category` model: unique `name`, self `parent` (PROTECT, `related_name="children"`), `has_products`/`has_subcategories` with the exactly-one `CheckConstraint`, and `created_at`/`updated_at` (Unix seconds via an abstract `TimestampedModel` and `unix_now()`, with `save()` setting `updated_at`). Add the migration. Verify with tests: duplicate names and both/neither flags raise `IntegrityError`, and an edit changes `updated_at` but not `created_at`.
- [x] 2.2 Add the `CATALOG_MAX_CATEGORY_DEPTH` setting (default 3) and implement `Category.clean()`: loop check, depth check, subtree depth when moving, parent must hold subcategories, the deepest level must hold products, and kind changes are blocked while in use. Verify that tests cover every scenario in `specs/category-hierarchy` (including depth 2 via `override_settings`).
- [x] 2.3 Implement `CategoryTree` (`category_tree.py`): one query; nodes in depth-first order with depth, `path()`, `descendant_ids()`; cached with `get_or_set` and a 1-hour timeout. Verify with unit tests for paths and descendants, and that `assertNumQueries(0)` holds on a warm cache.
- [x] 2.4 Add the `post_save`/`post_delete` receivers in `signals.py` that clear the cache through `transaction.on_commit` (registered in `AppConfig.ready`). Verify with tests that rename, move and delete show up on the next read, and that a rolled-back save leaves the cache intact (`captureOnCommitCallbacks`).
- [x] 2.5 Add the `Category` admin: a radio choice for the kind that sets both flags, a parent dropdown limited to `has_subcategories`, list display with full path and product count. Verify with admin tests: a GET on the changelist returns 200, a delete with products shows the protected page, and an invalid parent shows a form error.
- [x] 2.6 Document the category rules, the depth setting, and the risk of lowering the depth in the README. Verify the README section exists and matches the setting name.

## 3. Products and tags

- [x] 3.1 Add the `Tag` model (unique `name`) and the `Product` model (unique `name`, `description`, `price_cents` ≥ 0, `items_available` ≥ 0 as DB `CheckConstraint`s, `category` PROTECT, `tags` M2M), both inheriting `TimestampedModel`. Add the migration. Verify with tests: duplicate names and negative price or stock are rejected, and editing a tag or a product updates `updated_at` but not `created_at`.
- [x] 3.2 Implement `Product.clean()` (the category must hold products) and the admin `limit_choices_to={"has_products": True}`. Verify with a test that a subcategory-holding category fails validation and is missing from the admin form choices.
- [x] 3.3 Add the `money` template filter (cents → "$49.00") and a Unix-time display helper. Verify with unit tests, including 0 and large values.
- [x] 3.4 Add the `Product` and `Tag` admins: `list_display` (name, category path, price, stock), `list_filter` (category, tags), `search_fields`, `filter_horizontal` for tags, `list_select_related`, and read-only timestamps shown as dates. Verify that the changelist query count doesn't grow with the number of rows (`assertNumQueries` at 5 and at 20 products).
- [x] 3.5 Document the price-in-cents and Unix-timestamp conventions in the README. Verify the section exists.

## 4. Search and filtering

- [x] 4.1 Implement the `ProductQuerySet` methods `search`, `in_category` (via `CategoryTree.descendant_ids`), `with_tags(ids, match)` (subquery on the through table, design D4), `price_between`, `in_stock` and `for_listing` (`select_related`/`prefetch_related`, ordered by name). Verify with unit tests for every `specs/product-search` scenario that doesn't need favourites, including ANY returning no duplicate rows.
- [x] 4.2 Implement `ProductFilterSet` (`q`, `category`, `tags`, `match`, `price_min`, `price_max`, `include_out_of_stock`) calling the queryset methods, with form validation (unknown category, min > max). Verify with tests that invalid input makes the form invalid with field errors, and that combined filters match the spec's combined scenario.
- [x] 4.3 Add a query-count test for a filtered listing. Verify that pages of 5 and 20 products use the same number of queries.
- [x] 4.4 Document the search and filter behaviour (every word must match, `icontains` limits, ALL/ANY, category includes descendants, out-of-stock hidden by default) in the README "Assumptions" section. Verify the section exists.

## 5. Storefront (core page)

- [x] 5.1 Create the `base.html` layout (header with search input and user menu; sidebar and main column) and the `ProductListView` using the FilterSet, with 12 items per page. Verify with a test: GET `/` returns 200 and lists in-stock products for an anonymous user.
- [x] 5.2 Build the sidebar as one GET form: the category radio tree widget (indented by depth from `CategoryTree`, with "All" first), tag checkboxes, ALL/ANY radios, an include-out-of-stock checkbox, Apply/Reset; the header search input joined through the `form=` attribute. Verify with tests that a URL with filters renders the controls in their selected state and that Reset clears them.
- [x] 5.3 Add the price sliders (bounds from `aggregate(Min, Max)`, step 100 cents, inline JS for the labels). Verify with a test that the slider bounds match the cheapest and most expensive prices, and that filtering works through the query string without JS.
- [x] 5.4 Render product cards (name, category path, tags, price, stock or "Out of stock") and pagination that keeps the filters. Verify with tests that page 2 keeps the filters and out-of-stock cards have no Buy control.
- [x] 5.5 Add login and logout (`django.contrib.auth` views, `registration/login.html`, POST logout) and the header username. Verify with a test that logging in redirects to `next` and the header shows the username.
- [x] 5.6 Check by hand in the browser: load the page, combine search, category, tags and price, and confirm the results. Record the outcome in the task notes.
  - _Note (2026-11-22):_ checked in the browser with the demo fixtures. Typing "wireless" in the header, choosing Audio, ticking `budget`, dragging max price to $100 and pressing Search gave `?q=wireless&category=2&price_min=400&price_max=10000&tags=3&match=all` and exactly one product (Pebble Wireless Earbuds), with all controls shown as selected. The default listing showed 23 of 25 products (2 out of stock hidden).

## 6. Demo data and core milestone

- [x] 6.1 Run migrations, create a superuser, and enter at least 5 categories (a 3-level tree), at least 10 tags and at least 20 products (a range of prices, several tags each, at least 1 with stock 0) through the admin. Export to `catalog/fixtures/catalog.json` with `dumpdata catalog.category catalog.tag catalog.product --indent 2`. Verify the counts by loading it into a fresh database.
- [x] 6.2 Create `catalog/fixtures/demo_users.json` with an `admin` superuser and a `shopper` (`is_staff=False`), passwords stored as `make_password` hashes. Verify with tests: the admin can open `/admin/` and the shopper is redirected to the admin login.
- [x] 6.3 Add a fixture test that loads both fixtures and runs `full_clean()` on every record. Verify it passes.
- [x] 6.4 Add the demo credentials, fixture load order and a "never load demo_users in production" warning to the README. Verify the full README setup from a fresh clone ends with a working storefront and admin.

## 7. Favourites

- [x] 7.1 Add the `Favorite` model (user and product CASCADE, `TimestampedModel`, `UniqueConstraint(user, product)`) and the migration. Verify with a test that a duplicate pair raises `IntegrityError` and deleting a user removes their favourites.
- [x] 7.2 Add the `favorites_of(user)` and `with_is_favorite(user)` (`Exists`) queryset methods and the `favorites` FilterSet param (ignored for anonymous users). Verify the favourites scenarios in `specs/product-search` and `specs/favorites`, and that the query count stays fixed with `is_favorite`.
- [x] 7.3 Add the storefront favourite add/remove POST views (`login_required`, `require_POST`, safe `next` redirect), card toggle controls, the only-favourites checkbox for logged-in users, and the My favourites page (including out-of-stock products). Verify with tests: add and remove can be repeated safely, an anonymous visitor is redirected to login, an external `next` falls back to `/`, and GET returns 405.
- [x] 7.4 Add a few `catalog.favorite` rows for `shopper` to `demo_users.json`. Verify the fixture test still passes and the shopper sees at least 2 favourites.

## 8. Checkout and orders

- [x] 8.1 Add the `Order` (user PROTECT, `total_cents`) and `OrderItem` (order CASCADE, product PROTECT, `quantity` > 0 check, `unit_price_cents`, `UniqueConstraint(order, product)`) models, both inheriting `TimestampedModel`, and the migration. Verify with tests: the constraints reject quantity 0 and a duplicate product; deleting an ordered product or a user with orders is refused; rows created through `bulk_create` get both timestamps.
- [x] 8.2 Implement `place_order(user, items)` and `OutOfStock` per design D7. Verify with tests: success decrements stock and copies prices; one short item rolls back everything and lists every short product; repricing later leaves the order unchanged; sequential competing orders for the last unit give exactly one success; `updated_at` is set.
- [x] 8.3 Add a concurrency test (`TransactionTestCase`, two threads, file-based SQLite test database) for the last unit. Verify that exactly one order succeeds and stock ends at 0, or document a justified skip.
- [x] 8.4 Add the storefront Buy POST view (1 unit, success/out-of-stock messages, safe redirect) and the My orders page (`prefetch_related("items__product")`, newest first). Verify with tests: Buy creates an order and decrements stock, a sold-out Buy shows the message and creates nothing, and the My orders query count stays fixed.
- [x] 8.5 Add the read-only `Order` admin with inline items (no add, change or delete). Verify with an admin test that the change view renders and the add and delete permissions are denied.
- [x] 8.6 Document checkout behaviour (all-or-nothing, prices copied at purchase, SQLite concurrency notes) in the README. Verify the section exists.

## 9. Catalog API and OpenAPI docs

- [x] 9.1 Add the DRF, django-filter and drf-spectacular settings (default permission `IsAuthenticated`, pagination 20) and `/api/` routing. Verify `manage.py check` passes and `/api/schema/` returns 200.
- [x] 9.2 Implement the read-only `ProductViewSet` (shared FilterSet, `is_favorite` for logged-in users, category path, formatted price, timestamps), `CategoryViewSet` and `TagViewSet` with `AllowAny`. Verify with API tests: anonymous list and detail return 200, POST/PUT/DELETE return 405, invalid filters return 400 with field errors, and `favorites=true` while anonymous returns 401.
- [x] 9.3 Add a parity test. Verify the same query string returns the same product ids in the same order from the storefront and from `/api/products/` (collecting all pages).
- [x] 9.4 Configure Swagger UI at `/api/docs/` and add `@extend_schema` annotations where needed. Verify that the schema lists every product filter parameter and the 409 response, and that `/api/docs/` returns 200.
- [x] 9.5 Document the API endpoints and the docs URL in the README. Verify the section exists.

## 10. API authentication (JWT)

- [x] 10.1 Add simplejwt with the `token_blacklist` app, lifetimes from env (15 min / 1 day), rotation and blacklist after rotation, authentication classes `[JWTAuthentication, SessionAuthentication]`, and the routes `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/logout/`. Verify with tests: a valid login returns a token pair, a wrong password returns 401, an expired token returns 401, a reused refresh token returns 401, refresh after logout returns 401, and anonymous requests get 401 with `WWW-Authenticate: Bearer`.
- [x] 10.2 Verify session authentication on the API: a logged-in session reads `/api/orders/`, and a session POST without a CSRF token gets 403 (DRF `APIClient(enforce_csrf_checks=True)`).
- [x] 10.3 Document how to get and use tokens (curl and Swagger "Authorize") and the token lifetimes in the README. Verify the documented curl commands work against `runserver`.

## 11. Favourites and orders API

- [x] 11.1 Implement `FavoriteViewSet` (list, create returning 201 or 200 if it exists, destroy by `product_id` returning 204 whether or not it existed; queryset scoped to `request.user`). Verify every favourites scenario in `specs/catalog-api` with tests, including an unknown product returning 400 and user B being unable to see A's favourites.
- [x] 11.2 Implement `OrderViewSet` (list, retrieve, create) with the write serializer checks (empty list, quantity < 1, unknown product, duplicate product → 400) and `OutOfStock` → 409 listing every short product. Verify with tests: 201 with total, 400 cases, 409 with both ids, other users' orders return 404, and anonymous requests return 401.
- [x] 11.3 Verify the Swagger docs for these endpoints by hand: authorize with a JWT access token and call GET `/api/favorites/` and POST `/api/orders/` from `/api/docs/`.
  - _Note (2026-11-22):_ in `/api/docs/`, not logged in to the site, authorized `jwtAuth` with a shopper access token from `/api/auth/token/`. GET `/api/favorites/` returned 200 with the 4 fixture favourites; POST `/api/orders/` with `{"items": [{"product": 21, "quantity": 1}]}` returned 201 with total `$9.99`. A malformed body returned a JSON 400, not a stack trace.

## 12. Web security

- [x] 12.1 Add django-cors-headers per design D11 (env allowlist, API-only regex, no credentials, methods GET/HEAD/OPTIONS/POST/DELETE). Verify with tests: an allowed origin gets the allow header on `/api/products/`; unlisted origins and storefront paths get none; there's no `Access-Control-Allow-Credentials`; a PUT preflight doesn't list PUT.
- [x] 12.2 Add CSRF tests across the storefront and admin. Verify that Buy, favourite and admin POSTs without a token get 403 (`Client(enforce_csrf_checks=True)`) and that pages send `X-Frame-Options: DENY`.
- [x] 12.3 Verify that `manage.py check --deploy` reports no issues with production env values (`DEBUG=0`, real `SECRET_KEY`, hosts set), and add it as a test or a documented command.
- [x] 12.4 Document the environment variables (table), CORS configuration and the security notes in the README. Verify it matches `.env.example`.

## 13. Final integration checks

- [x] 13.1 Run the full test suite from a fresh clone (`uv sync`, migrate, `uv run python manage.py test`). Verify everything passes with no warnings about unapplied migrations (`makemigrations --check`).
- [x] 13.2 Walk through the README end to end by hand: admin login and edit, storefront filters, favourite, Buy, My orders, Swagger with JWT. Confirm every spec capability can be seen working.
  - _Note (2026-11-22):_ walked through in the browser against a database loaded from the fixtures. Admin: logged in as `admin`, changed Yoga Mat Pro's price to 599 cents (list showed $5.99 and a new updated time), and renamed Audio to Sound, which the storefront showed straight away (cache cleared). Storefront: combined filters (see 5.6); as `shopper`, logged in from a filtered page and came back to it, favourited Pebble Wireless Earbuds (♥ shown), bought one (order #1 message, stock 40 → 39), and saw it in My orders ($39.00) and in My favourites alongside the out-of-stock Kids Safe Headphones. API: Swagger with a JWT (see 11.3), session GET `/api/orders/` 200, and session POST without CSRF 403. The dev database was reset from the fixtures afterwards.
- [x] 13.3 Finish the README with "Known limitations" and "Future work" (FTS5 full-text search, a cart, a shared cache backend, CSP/rate limiting). Re-check that the Project description, the Features checklist (every item ticked and matching a spec capability) and the Workflow section match the finished app. Verify that it covers every risk listed in design.md and that each workflow step works as described.

## Workflow follow-up

- Initialise git, commit, and push to a **public** GitHub repository as the assignment requires, once the user approves publishing.
- Archive the change with `/opsx:archive` after review.
