# Tasks

## 1. Product slug and picture fields

- [x] 1.1 Add `Product.image_url` (`URLField`, max 500, blank, http/https only) and `Product.slug` (`SlugField`, max 220). Use a three-step migration: add the slug as nullable, fill it with `RunPython`, then make it unique and non-null. Verify that `manage.py migrate` on a copy of the current `db.sqlite3` fills a slug for all 25 products and that `makemigrations --check` reports no changes.
- [x] 1.2 Generate a missing slug in `Product.save()` from `slugify(name)`, with a `-2`, `-3`… suffix on collision and a `"product"` fallback. Verify with new `test_catalog_data.py` tests:
  - a generated slug;
  - a colliding slug (`c-primer-2`);
  - a rename keeps the slug;
  - a duplicate hand-set slug is rejected;
  - a `javascript:` picture URL fails `full_clean`.
- [x] 1.3 Add `slug` (prepopulated from `name` when adding) and `image_url` to the `ProductAdmin` fields. Verify with an admin test that the add and change forms show both fields.
- [x] 1.4 Add `slug` and `image_url` to `ProductSerializer` (empty string when no picture). Verify with `test_api.py` tests that list and detail responses include both and that `/api/schema/` lists them.

## 2. Product page and pictures

- [x] 2.1 Add `ProductDetailView` at `products/<slug:slug>/`, built on `Product.objects.for_listing(user)`, and a `catalog/product_detail.html` template. The page shows the picture, the full description, the category path, tags, price, stock, Buy when in stock and the favourite control for logged-in users. Verify with `test_storefront.py` tests:
  - the page renders by slug;
  - an unknown slug returns 404;
  - an out-of-stock product shows no Buy;
  - Buy and favourite on the page redirect back to it.
- [x] 2.2 Add a `_product_image.html` include that renders the `<img>` (lazy, `no-referrer`, alt = name, `onerror` swaps in the placeholder) or a neutral placeholder block, both with the same aspect ratio. Use it on cards and the product page. Verify with a template test that both the image and the placeholder render, and in the browser preview that a broken URL shows the placeholder.
- [x] 2.3 Update `_product_card.html`: picture, a **Details** link to the product page, and **Buy** for in-stock products for everyone. For anonymous visitors Buy is a link to login with `next` set to the current page. Remove the "Log in to buy or save favourites" text. Update `test_storefront.py`, replacing the "Log in" assertion at line 37. Verify that an anonymous visitor sees Details and Buy and no favourite control, that following Buy and logging in returns to the same filtered URL, and that no order is created.
- [x] 2.4 Update the README walkthrough (steps 2–5) to describe Details, the product page and Buy for anonymous visitors. Verify that the README matches the behaviour in the browser preview.

## 3. Accounts: sign-up and login by email

- [x] 3.1 Add `EmailAuthenticationForm`: "Email" label, lower-cased username. Route `accounts/login/` to `LoginView` with that form, declared before the `django.contrib.auth.urls` include. Update `registration/login.html` with the "Email" label and a sign-up link that carries `next`. Verify with `test_auth.py` tests that a mixed-case email logs in and that a wrong password shows the generic error.
- [x] 3.2 Add `SignUpForm` and a sign-up view at `accounts/signup/`, with a `registration/signup.html` template that links to login and carries `next`. The form lower-cases the email, rejects duplicates ignoring case, checks that the passwords match and runs `validate_password`. The view creates the user with username = email, logs them in and redirects to `safe_next`. Logged-in users are redirected home. Verify with a new `test_accounts.py` covering every `accounts` spec scenario:
  - success;
  - a non-staff account;
  - `Ann@Example.com` stored lower-cased;
  - a duplicate email;
  - an invalid email;
  - passwords that don't match;
  - a weak password;
  - the `next` round trip with no order;
  - an external `next`;
  - a logged-in user is redirected.
- [x] 3.3 Update test helpers that log in by username (`factories.user`, `test_auth.py`, `test_storefront.py`) only where the new login form changes behaviour. Verify that the full test suite passes.
- [x] 3.4 Document sign-up and login by email in the README. Verify that the documented URLs work in the browser preview.

## 4. Sidebar: collapsible tree, price slider, Apply/Reset

- [x] 4.1 Extend `CategoryTreeWidget` and `widgets/category_option.html` to output `data-id`, `data-parent` and `data-has-children` for each option. Keep the `depth-N` classes so `test_storefront.py:117-118` still passes. Verify with a test that "Headphones" carries the parent id of "Audio" and that "Electronics" is marked as having children.
- [x] 4.2 Add the tree script:
  - add arrow toggle buttons (`aria-expanded`);
  - collapse all categories on load;
  - expand the ancestors of the checked category;
  - the arrow toggles a branch and the label only selects.

  Verify in the browser preview:
  - the tree starts collapsed;
  - the arrow expands a branch without selecting it;
  - a name selects without toggling;
  - `?category=<Headphones id>` reveals Electronics > Audio > Headphones;
  - with JavaScript disabled the whole tree shows.
- [x] 4.3 Turn the two price inputs into one track with two handles. The script adds a `dual` class; CSS stacks the inputs, with pointer events on the thumbs only and a filled range between them. Keep the clamping and labels. Verify in the browser preview that the handles cannot cross and the labels update, and that without JavaScript two separate sliders filter correctly. The existing price filter tests must still pass.
- [x] 4.4 Compute `filters_active` in `ProductListView`. The defaults are an empty search, no category or tags, ALL matching, price at the slider bounds and the stock/favourites options off. When nothing is active, render Reset as disabled (`aria-disabled`, no `href`). Verify with tests: no filters → disabled; a category → enabled; price equal to the bounds only → disabled.
- [x] 4.5 Add the Apply-state script. It snapshots `new FormData(form)`, including the header search, as a sorted query string; it enables Apply only when the current values differ from the snapshot. The server renders Apply enabled. Verify in the browser preview: disabled on load; ticking a tag enables it; unticking disables it again; typing in the search box enables it.
- [x] 4.6 Restructure the sidebar into a scrolling `.filters-body` and a `.filter-actions` footer. On desktop the `aside` is sticky with the actions at its bottom. Below 760px the actions become a fixed bottom bar, with matching bottom padding on `main`. Verify in the browser preview at desktop width and with `resize_window` mobile (375px) that Apply and Reset stay visible while scrolling and that the last card and the pagination are not covered.

## 5. Demo data and page size

- [x] 5.1 Set `CATALOG_PAGE_SIZE = 10`. Verify with a test that 25 matching products give pages of 10, 10 and 5.
- [x] 5.2 Find a picture URL for each of 24 products, leaving one book without one. Prefer direct `upload.wikimedia.org` file URLs, with `images.unsplash.com` as a fallback. Verify that each URL returns an image (HTTP 200 with an `image/*` content type).
- [x] 5.3 Rebuild `catalog.json` with a throwaway script on a fresh database loaded with the old fixtures:
  1. Move products into Books, Headphones, Speakers, Computers & Phones and Home & Outdoors.
  2. Delete the obsolete categories.
  3. Rename and convert the target categories.
  4. Fill the slugs and pictures. Keep the product ids.
  5. Export with `dumpdata catalog.category catalog.tag catalog.product --indent 2`.

  Verify that the 7 category paths match the `demo-data` spec, that there are 25 products, and that `test_every_record_passes_full_clean` passes.
- [x] 5.4 Update `demo_users.json`:
  - rename `admin` and `shopper` to `admin@example.com` and `shopper@example.com`, setting username and email and keeping their hashes;
  - add `shopper2@example.com` with a `make_password("demo-shopper2-123")` hash and no favourites.

  Verify with an updated `test_demo_data.py`:
  - email logins for all three accounts;
  - both shoppers are denied the admin;
  - the first shopper has at least 2 favourites;
  - the second shopper has none.
- [x] 5.5 Add `test_demo_data.py` checks for the exact 7 category paths, 25 products, at least one product without a picture and more than one storefront page. Verify that they pass on the new fixtures.
- [x] 5.6 Update the README:
  - the demo logins table (three email accounts);
  - the curl example (`shopper@example.com`);
  - the fixture description (7 categories, pictures);
  - a note that pictures need internet access;
  - the reload steps (`flush`, then `loaddata catalog demo_users`).

  Verify that the documented commands run as written on a fresh database.

## 6. Integration check

- [x] 6.1 Run the full test suite (`uv run --env-file .env python manage.py test`) and `manage.py check --deploy` with production-like settings. Verify that both pass.
- [x] 6.2 Reload the demo database (`flush`, `loaddata catalog demo_users`) and walk through the storefront in the browser preview:
  1. As an anonymous visitor: browse, use the collapsed tree, filter by price, open Details, click Buy.
  2. Sign up as a new email from the login page.
  3. Confirm you return to the product page without an order.
  4. Log in as `shopper@example.com` and buy.
  5. Check the mobile width.

  Verify that every step behaves as the specs describe, and capture a screenshot.
