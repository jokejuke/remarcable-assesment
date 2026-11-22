# Design

## Context

- The storefront is server-rendered Django with inline CSS in `base.html` and one small inline script in `product_list.html`. There is no static build step and no front-end library. Filtering must keep working without JavaScript (`storefront` spec, "Price sliders").
- The category radios come from `CategoryTreeWidget` in `catalog/filters.py`. It renders a **flat** list of options with a `depth-N` class, built from the cached `CategoryTree`.
- Anonymous POSTs to `buy` already redirect to login with `next` (`login_required_action` in `catalog/views.py`). Only the card template hides the button.
- Login is Django's stock `LoginView`, via the `django.contrib.auth.urls` include in `config/urls.py`. Usernames are arbitrary strings. API tokens (`/api/auth/token/`) authenticate with the same username.
- No Content Security Policy is set, so pictures from other sites and inline event handlers load without any setting change.
- The demo fixtures were exported with `dumpdata`. `demo_users.json` refers to product ids 1, 4, 5 and 22 through favourites.

## Goals / Non-Goals

**Goals:**
- Every new interaction is a progressive enhancement: the page still works, less smoothly, without JavaScript.
- Add no new Python or JavaScript dependencies.
- Keep existing filter query parameters and API URLs (products by id) unchanged.

**Non-Goals:**
- Email verification, password reset and rate limiting for sign-up or login.
- Uploading or hosting pictures. Only a URL is stored.
- Case-insensitive login for the admin login form and the API token endpoint. They keep exact matching; every stored username is lower case anyway.
- Redirects from old id-based product URLs. Product pages never had them.

## Decisions

### 1. Collapsible tree: enhance the flat radio list with a script, not nested `<details>`

- The widget adds `data-id`, `data-parent` and `data-has-children` to each option label.
- On load, a script:
  - inserts a `<button type="button" aria-expanded>` arrow before each parent's radio;
  - hides every option whose ancestor is collapsed;
  - expands the ancestors of the checked option.
- The arrow toggles visibility. The label still selects the radio.
- Without JavaScript nothing is hidden, so the page behaves as it does today.

*Alternative:* nested `<details>/<summary>`. Clicking anywhere in a `<summary>` toggles it, so a radio and its label inside a summary would both select and expand, which conflicts with the spec. It would also mean rewriting the widget to output nested markup instead of a flat choice list.

### 2. Dual price slider: two stacked native range inputs

The script adds a `dual` class to the price fieldset. CSS then:
- stacks both inputs on one track;
- sets `pointer-events: none` on the inputs and `auto` on their thumbs;
- draws the filled segment between the handles with a linear gradient driven by CSS custom properties.

The existing `sync()` clamping (min ≤ max) and live labels stay. Without the class, the two sliders render separately, as they do today.

*Alternative:* a slider library such as noUiSlider. Rejected: it would be a new dependency, and the project has no asset pipeline to bundle it.

### 3. Apply state in the browser; Reset state on the server

- **Apply:** on load, the script snapshots the form as a sorted `URLSearchParams` string built from `new FormData(form)`. That includes the header search box, which belongs to the form through `form="filters"`. On every `input`/`change` event it compares the current string with the snapshot and toggles `disabled`. The server always renders Apply enabled, so the page works without JavaScript.
- **Reset:** the view computes `filters_active` from the cleaned filter data: any of `q`, `category`, `tags`, `include_out_of_stock` or `favorites` set, `match=any` with tags, or a price bound different from the slider bounds. When nothing is active, Reset renders as `<a class="button secondary" aria-disabled="true">` without an `href`.
- Computing Reset on the server keeps it correct without JavaScript, and matches the spec's notion of defaults.

### 4. Always-visible actions: a sticky sidebar with its own scrolling area

- The form becomes a flex column: a scrolling `.filters-body` holding the fieldsets, then `.filter-actions` holding the buttons.
- On wide screens the `aside` is `position: sticky; top: 0; max-height: 100vh`, so the actions stay at its bottom.
- Below 760px, `.filter-actions` becomes `position: fixed; bottom: 0` across the full width, and `main` gets bottom padding equal to the bar's height so the last card and the pagination stay reachable.
- This is pure CSS and works without JavaScript.

### 5. Product slug: a stored `SlugField`, generated once

- The field is `Product.slug = SlugField(max_length=220, unique=True)`.
- When the slug is empty, `Product.save()` fills it with `slugify(name)`, falling back to `"product"` for names that yield nothing. It appends `-2`, `-3`, … until the slug is unique.
- The admin uses `prepopulated_fields = {"slug": ["name"]}`, which Django runs only while adding a product, so renaming never rewrites the slug. The slug stays editable.
- A three-step migration adds the field:
  1. add it as nullable and non-unique;
  2. fill it with the same function (`RunPython`, reversible as a no-op);
  3. make it unique and non-null.
- Generating the slug in `save()` means objects created in code or tests get one automatically. *Alternative:* computing it from the name on each request. Rejected: you chose a stored, stable slug.

### 6. Product page view and URL

- `path("products/<slug:slug>/", ProductDetailView)` is added next to the existing `products/<int:product_id>/…/` action routes. The patterns cannot collide because the action routes have a further path segment.
- The view's queryset is `Product.objects.for_listing(request.user)`, so `is_favorite` and the prefetched tags work as they do on cards.
- Buy and favourite forms on the page post `next=` the page's own URL. The existing `safe_next` sends the user back there.

### 7. Picture: `URLField` restricted to http/https, with a placeholder fallback

- The field is `Product.image_url = URLField(max_length=500, blank=True, validators=[URLValidator(schemes=["http", "https"])])`.
- A shared `_product_image.html` include renders:
  - `<img src alt="{{ name }}" loading="lazy" referrerpolicy="no-referrer" onerror="…">` when the URL is set;
  - a neutral `.img-placeholder` block (a CSS box with an inline SVG) otherwise.
- `onerror` swaps a failed picture for the placeholder.
- Both use the same `aspect-ratio`, so cards line up.
- *Alternative:* attaching error listeners from a script at the end of the page. Rejected: a picture can fail before that script runs. The inline handler would need revisiting if a strict CSP is ever added. That is noted as a risk.

### 8. Anonymous Buy: a link to login, not a POST

- For anonymous visitors, the card and the product page render Buy as `<a class="button buy" href="{% url 'login' %}?next=<current page>">`. A `login_required_action` POST would land in the same place, but a link needs no CSRF token on cache-friendly anonymous pages and cannot create an order by accident.
- The decorator stays as the server-side guard.
- The favourite control stays hidden for anonymous visitors, as the spec requires.

### 9. Accounts: a small sign-up view and a case-insensitive login form

- `SignUpForm` (a plain `forms.Form`) has fields `email`, `password1` and `password2`. Its checks:
  - It lower-cases the email.
  - It rejects an email when `User.objects.filter(username__iexact=email)` exists.
  - It runs `validate_password` against an unsaved `User(username=email, email=email)`, so `UserAttributeSimilarityValidator` applies.
- The view creates the user with `create_user(username=email, email=email, password=…)`, calls `login()`, and redirects to `safe_next`. Logged-in users who open it are redirected home.
- `EmailAuthenticationForm(AuthenticationForm)` labels the username field "Email" and lower-cases it in `clean_username`.
- Routes `accounts/login/` (with that form) and `accounts/signup/` are declared before the `django.contrib.auth.urls` include, so they take precedence. Logout and the other auth routes are unchanged.
- *Alternative:* a custom case-insensitive authentication backend. That would also affect the admin and the API token endpoint, which is broader than asked and harder to reason about.

### 10. Demo data: rebuild with a one-off script, then `dumpdata`

- A throwaway script (not committed), run against a fresh database with the old fixtures loaded:
  1. Moves products into the 7 target categories.
  2. Deletes the 8 obsolete categories.
  3. Renames "Computers" to "Computers & Phones" and switches it to hold products, which `clean()` allows once its children are gone.
  4. Renames "Home & Kitchen" to "Home & Outdoors" in the same way.
  5. Flattens "Books" into a product-holding category.
  6. Fills `slug` and `image_url`.
- The result is exported with `dumpdata catalog.category catalog.tag catalog.product --indent 2`.
- Product ids are kept, so the favourites in `demo_users.json` still resolve.
- `demo_users.json` is edited by hand:
  - usernames and emails become `admin@example.com` and `shopper@example.com`, keeping their password hashes;
  - a third user `shopper2@example.com` is added with a hash from `make_password("demo-shopper2-123")`.
- `FixtureValidationTests.test_every_record_passes_full_clean` still guards every record.
- **Picture sources:** prefer direct `upload.wikimedia.org` file URLs (Wikimedia Commons, freely licensed, stable). Fall back to `images.unsplash.com` URLs. One book is left without a picture to show the placeholder.

### 11. Page size

- `CATALOG_PAGE_SIZE` changes from 12 to 10.
- The API's `REST_FRAMEWORK["PAGE_SIZE"]` (20) is unchanged.

## Risks / Trade-offs

- [Pictures linked from other sites disappear or are blocked] → The placeholder fallback keeps the layout intact. The README states that pictures need internet access.
- [Renamed demo logins surprise anyone used to `shopper`] → The README table and the curl example are updated in the same change.
- [Category ids change in the fixture, so an existing `db.sqlite3` with old demo data is inconsistent] → The migration plan says to reload the demo data into a fresh database.
- [Inline `onerror` handlers conflict with a future strict CSP] → They're confined to one include, so they're easy to replace with a script-based listener if a CSP arrives.
- [Disabled Apply could confuse users whose browser autofilled values] → The snapshot is taken after load, so autofilled values count as the starting state. Apply enables on the first real change.
- [The sticky sidebar plus a fixed mobile bar can cover content] → Bottom padding on `main` matches the bar's height. A spec scenario checks that the last card can be reached.

## Migration Plan

1. `migrate` adds `image_url` and `slug` and fills slugs for existing products.
2. For a demo database, reload all data. The category tree changed and products keep their ids:
   - `flush`
   - `loaddata catalog demo_users`
3. **Rollback:** reverse the migration. Both fields are dropped, and the slug fill step reverses as a no-op. Then restore the previous fixtures from git.
