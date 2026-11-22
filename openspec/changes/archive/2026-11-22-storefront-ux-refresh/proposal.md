# Proposal

## Why

The storefront works but is awkward to use. The category tree shows all 15 categories at once. Price takes two separate sliders. Apply and Reset scroll out of view. Products have no page or picture of their own. Anonymous visitors see no Buy button, and they have no way to create an account. This change makes the storefront feel like a shop without changing how search, favourites or checkout work underneath.

## What Changes

- **Collapsible category tree:** categories start collapsed. An arrow next to a category expands it, and clicking the name selects it. The branch that holds the selected category opens on page load. Without JavaScript the full tree is shown, as it is today.
- **One price track with two handles** replaces the two separate sliders. The query parameters (`price_min`, `price_max`) are unchanged. Without JavaScript the two native sliders remain.
- **Apply and Reset states:** Apply is disabled until a filter control changes. Reset is disabled when no filter differs from the defaults.
- **Apply and Reset always visible:** pinned to the bottom of the sidebar on desktop, and in a fixed bar at the bottom of the screen on narrow screens.
- **Product cards** show a picture, a **Details** link and a **Buy** button for everyone. Logged-out users who click Buy go to the login page. After logging in they return to the page they came from, and nothing is bought. **BREAKING** (UI): the "Log in to buy or save favourites" link on cards is removed.
- **Product page** at `/products/<slug>/` with the picture, the full description, the category path, tags, price, stock, Buy and the favourite toggle. The slug is the only public URL for a product.
- **Product slug:** a new unique `slug` field, generated from the name when the product is created. Administrators can edit it, and it does not change when the product is renamed.
- **Product picture:** a new optional `image_url` field (one picture per product). Cards and the product page show a neutral placeholder when it is empty or the picture fails to load.
- **Sign-up page:** a visitor creates an account with an email address and a password. The email address becomes the username. The login page links to sign-up and back, and both keep the `next` target.
- **Login by email:** the login field is labelled "Email" and matching ignores letter case.
- **API:** product responses gain `slug` and `image_url`, both in lists and on a single product.
- **Demo data:**
  - **BREAKING** (demo logins): accounts are renamed to `admin@example.com` and `shopper@example.com`.
  - A second shopper is added: `shopper2@example.com`, with no favourites.
  - The category tree shrinks from 15 to 7 categories, still 3 levels deep. All 25 products are kept and reassigned.
  - Every product except one gets an `image_url` from Wikimedia Commons or Unsplash.
- **Pagination:** storefront pages hold 10 products instead of 12. The API page size is unchanged.

## Capabilities

### New Capabilities
- `accounts`: Visitor sign-up with email as the username, and login by email address.

### Modified Capabilities
- `storefront`:
  - Cards show a picture, Details and Buy for every visitor.
  - New product page.
  - Collapsible category tree.
  - A single dual-handle price slider.
  - Apply/Reset active states and always-visible placement.
  - 10 products per page.
  - Login page links to sign-up.
- `catalog-data`:
  - Products gain a unique, stable `slug` and an optional `image_url`.
  - Both are editable in the admin.
- `catalog-api`: the product representation includes `slug` and `image_url`.
- `demo-data`:
  - Demo accounts log in with email addresses.
  - A second shopper.
  - 7 categories.
  - Product pictures, with one product left without a picture.

## Impact

- **Models and migrations:** `Product.slug` and `Product.image_url`. The slug migration fills slugs for existing rows before making the field unique.
- **Views and URLs:**
  - New product detail view at `products/<slug:slug>/`.
  - New sign-up view at `accounts/signup/`.
  - A login form that accepts the email address in any letter case.
- **Templates:**
  - `_product_card.html`, `product_list.html`, `base.html` (styles)
  - `registration/login.html`, new `registration/signup.html`, new `catalog/product_detail.html`
  - The category option widget template
- **Filters:** `CategoryTreeWidget` exposes each category's parent and whether it has children, so the tree can collapse.
- **Admin:** the product form gains `slug` (prepopulated from the name when adding a product) and `image_url`.
- **API:** `ProductSerializer` and the OpenAPI schema.
- **Settings:** `CATALOG_PAGE_SIZE` changes to 10.
- **Fixtures:** `catalog.json` (categories, product categories, slugs, images) and `demo_users.json` (renamed accounts, a new shopper).
- **Documentation and tests:** the README's demo logins, counts and curl example; tests that log in as `admin` or `shopper`.
- **No new dependencies.** Pictures are loaded straight from Wikimedia Commons or Unsplash, so the demo shows placeholders when offline.
