# Proposal

## Why

Review of the storefront found seven rough spots: relative imports, server-rendered favourite state on every card, UTC-only timestamps, product pictures that show blanks, an API login that still asks for a "username", a heavy category tree, and no favourites count. Fixing them together keeps one coherent pass over the UI.

## What Changes

- Use absolute `catalog.…` imports everywhere; put the repo root on the tool path (pytest, ruff) and forbid relative imports with a lint rule.
- **BREAKING (UI only)**: remove the favourite heart from product cards. Favourite state is shown only on the product page, filled in by a separate async request that returns the user's favourite product slugs.
- New endpoint `GET /api/favorites/slugs/` returning a flat list of slugs (session or token auth). The favourite toggle on the product page becomes an async add/remove call with no page reload.
- Show "My favourites (N)" in the navigation; the count comes from the same slugs request and follows toggles.
- Show timestamps in the viewer's local time, converted in the browser (My orders first); the UTC server text remains as the no-JavaScript fallback.
- Make every demo product's picture URL work: reload the fixture into the local database, add the one missing URL, and test that no fixture product lacks one. Pictures stay hotlinked URLs; nothing is downloaded or stored.
- Email everywhere for sign-in: the API token endpoint takes `email` (case-insensitive) instead of `username`; the header shows "Signed in as" the email.
- Simplify the category filter: selecting any category queries only descendant categories with `has_products = true`; the sidebar becomes nested native `<details>` with no JavaScript.

Out of scope: the Django admin login form (it keeps its own "Username" field; demo admin username is already an email), API `is_favorite` on products (unchanged), the "Only my favourites" sidebar filter and My favourites page (unchanged).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `storefront`: remove card favourite toggle; async favourite control on product page; favourites count in nav; client-side local time; simpler category tree.
- `favorites`: add the favourite slugs list.
- `catalog-api`: add `GET /api/favorites/slugs/`.
- `api-auth`: token endpoint authenticates by email.
- `accounts`: signed-in identity shown as email.
- `product-search`: category filter expands to product-holding categories only.
- `demo-data`: every demo product has a working picture URL.

## Impact

- Code: all modules in `catalog/` and `catalog/api/` (imports), `catalog/views.py`, `catalog/api/{views,serializers,urls}.py`, `catalog/querysets.py`, `catalog/category_tree.py`, `catalog/filters.py`, templates (`base.html`, `product_detail.html`, `product_list.html`, `_product_card.html`, `_product_actions.html`, `my_orders.html`, category widget), `catalog/templatetags/money.py`, `catalog/fixtures/catalog.json`, `pyproject.toml`, README.
- Tests: favourites, storefront, API, auth, category, demo-data suites updated.
- Local database must be reloaded from the fixtures to get picture URLs (destroys local data).
