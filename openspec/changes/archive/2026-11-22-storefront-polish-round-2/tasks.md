# Tasks

## 1. Absolute imports and tooling

- [x] 1.1 Rewrite every relative import in `catalog/` and `catalog/api/` to `catalog.…`; verify with `grep -rn "^from \.\|^from \. import" catalog` returning nothing and the full test suite passing
- [x] 1.2 Add pytest `pythonpath = ["."]`, ruff `src = ["."]` and rule `TID252` to `pyproject.toml`; verify `uv run ruff check` passes and a deliberately relative import is flagged

## 2. Category filter

- [x] 2.1 Add product-holding descendant lookup to `CategoryTree` and use it in `ProductQuerySet.in_category`; verify with tests that filtering a parent queries only `has_products` category ids and leaf/unknown behaviour is unchanged
- [x] 2.2 Replace the radio-tree widget and its toggle script with nested `<details>` (selected branch open, "All" first); verify the storefront category tests and a browser check of select/expand without JavaScript
- [x] 2.3 Remove the unused `category_option.html` and tree script; verify no references remain

## 3. Favourites

- [x] 3.1 Add `GET /api/favorites/slugs/` (session and token auth, constant queries); verify with API tests for content, empty list, other users' favourites, anonymous rejection and query count
- [x] 3.2 Remove the heart from cards and `_product_actions.html`; delete the redirecting favourite add/remove views, URLs and their tests; verify list pages render no favourite control
- [x] 3.3 Add the `base.html` script that fetches slugs, shows "My favourites (N)" and exposes the set; verify in the browser preview with a shopper that has two favourites
- [x] 3.4 Make the product-page favourite control async (add/remove via existing API with CSRF, revert on error, update badge); verify in the browser that toggling changes the heart and badge without reload and that anonymous users see a login link

## 4. Local time

- [x] 4.1 Change the `unixtime` filter to emit a `<time datetime>` with UTC fallback text and add the formatting script; verify a unit test of the markup and a browser check in a non-UTC time zone on My orders

## 5. Email credentials

- [x] 5.1 Make `/api/auth/token/` take `email` (case-insensitive) instead of `username`; verify tests for valid, mixed-case, wrong-password and username-only (400) cases
- [x] 5.2 Show the email in the header ("Signed in as …"), update README curl examples and OpenAPI docs; verify the accounts tests and README text

## 6. Pictures

- [x] 6.1 Add a working URL for "Starfall Chronicles" to the fixture and a test that every fixture product has an http(s) `image_url`; verify the test passes and the URL answers 200
- [x] 6.2 Document reloading fixtures in the README; after the user reloads, verify in the browser that cards show pictures, not placeholders

## 7. Wrap-up

- [x] 7.1 Update affected tests and README feature list; verify the full test suite passes and `openspec validate storefront-polish-round-2` succeeds
