# Design

## Context

The storefront is server-rendered Django with DRF under `/api/`. DRF already accepts JWT and session auth, with CSRF enforced for session writes (spec `api-auth`). Product pages and cards currently get `is_favorite` from a queryset annotation and toggle through redirecting form POSTs. Timestamps are Unix seconds rendered to UTC text by the `unixtime` filter. Categories are an immutable cached tree where `has_products` and `has_subcategories` are mutually exclusive, so products live only in leaf categories. The local `db.sqlite3` was loaded before `image_url` existed, so it has no picture URLs; the fixture URLs themselves respond 200.

## Goals / Non-Goals

**Goals:** one favourites data source for the badge and the product-page control; no per-card favourite state; browser-side time formatting; only-product-category queries; email-only credentials in the API.

**Non-Goals:** downloading or storing images; changing the Django admin login; removing `is_favorite` from the API product representation; changing the "Only my favourites" filter.

## Decisions

1. **Favourite slugs live at `GET /api/favorites/slugs/`** (a `@action` on `FavoriteViewSet`, `detail=False`), returning a bare JSON array via one `values_list("product__slug", flat=True)` query. Session auth already works with CSRF, so no new Django view is needed. Alternative: a plain Django JSON view — rejected, it would duplicate auth and sit outside the OpenAPI schema.
2. **One small script in `base.html`** (logged-in only) fetches the slugs once per page, writes N into the nav link, and exposes the set to the page. The product page reads it for the heart. Toggle uses the existing `POST /api/favorites/` (by product id from `data-product-id`) and `DELETE /api/favorites/{id}/`, with the CSRF token from the cookie, then updates the set and the badge. On failure it reverts the control and shows a message. Alternative: server-rendered count in the template — rejected, the requirement is a separate async request and it would go stale after toggles.
3. **Cards lose favourite state.** `_product_card.html` and `_product_actions.html` drop the heart; the list/detail views keep `for_listing(user)` untouched so the API still serves `is_favorite`. The detail template no longer reads `product.is_favorite`. Add/remove storefront views stay (used by no one after this, remove them with their URLs and tests to avoid dead code).
4. **Local time:** replace `unixtime` output with `<time datetime="…Z" class="local-time">UTC text</time>`; one script formats with `Intl.DateTimeFormat(undefined, {dateStyle:"medium", timeStyle:"short"})`. The filter stays a template-tag so every future timestamp uses it.
5. **Category query:** add `CategoryTree.product_descendant_ids(id)` (descendants with `has_products`) built from the existing cached rows; `in_category` uses it. Because a leaf's descendant set is itself, leaf queries are unchanged. The sidebar widget is replaced by a template that walks `category_tree` into nested `<details>`/radio inputs; the ~60-line toggle script and `category_option.html` are removed. Alternative: flat select of path labels — kept as a fallback if `<details>` nesting proves awkward with the sticky sidebar.
6. **Email token login:** subclass `TokenObtainPairSerializer` so the `email` field replaces `username`, lower-casing it before authentication. Update the OpenAPI schema, README curl example and tests. A request carrying only `username` gets 400.
7. **Imports and tooling:** rewrite relative imports to `catalog.…`; `pyproject.toml` gets `[tool.pytest.ini_options] pythonpath = ["."]` and ruff `src = ["."]` with rule `TID252` (ban relative imports). `config` already imports absolutely.
8. **Pictures:** fixture gets a URL for "Starfall Chronicles" (any CC-licensed hotlink, verified to answer 200); a test asserts every fixture product has an http(s) URL. The README tells users to reload the fixtures, since existing databases keep empty URLs.

## Risks / Trade-offs

- [Hotlinked pictures can break or be rate-limited by the host] → the existing placeholder fallback stays; accepted per the no-download decision.
- [Badge flashes without a number until the request returns] → render "My favourites" first, add "(N)" on response.
- [BREAKING API clients using `username` on the token endpoint] → README and spec updated; this is a take-home project with no known external clients.
- [Fixture reload deletes local data] → documented, user runs it.
- [`<details>` inside a scrolling sticky sidebar] → open state of the selected branch is server-rendered, so no layout JS is required.

## Migration Plan

Code and fixture change together; reload fixtures locally (`loaddata catalog demo_users` after flush, per README). Rollback is a git revert.
