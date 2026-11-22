## ADDED Requirements

### Requirement: Favourites count in navigation
For a logged-in user, the navigation link SHALL read "My favourites (N)" where N is the number of the user's favourites, loaded by a separate asynchronous request after the page renders. N SHALL update without a reload when the user adds or removes a favourite on a product page. Anonymous visitors SHALL see no such link.

#### Scenario: Badge shown
- **WHEN** a shopper with two favourites opens any page
- **THEN** the navigation shows "My favourites (2)"

#### Scenario: Badge follows toggle
- **WHEN** that shopper removes a favourite on a product page
- **THEN** the navigation shows "My favourites (1)" without a page reload

#### Scenario: No favourites
- **WHEN** a shopper with no favourites opens a page
- **THEN** the navigation shows "My favourites (0)"

### Requirement: Timestamps shown in local time
Timestamps on storefront pages SHALL be converted to the viewer's local time zone in the browser. The server SHALL render each as a `<time>` element carrying its ISO 8601 UTC value, with UTC text inside as the fallback when JavaScript is unavailable.

#### Scenario: Order time in local time
- **WHEN** a shopper whose browser is in UTC+2 opens My orders for an order placed at 10:00 UTC
- **THEN** the order shows 12:00

#### Scenario: Without JavaScript
- **WHEN** My orders is shown with JavaScript disabled
- **THEN** the order time shows in UTC, labelled UTC

## MODIFIED Requirements

### Requirement: Nested category tree in the sidebar
The sidebar SHALL show categories as a tree indented by level, with an "All" option at the top. The selected category SHALL be marked. Categories that have subcategories SHALL be nested native disclosure (`<details>`) elements, collapsed by default, with the branch containing the selected category open. Selecting a category SHALL NOT depend on JavaScript.

#### Scenario: Tree rendering
- **WHEN** the sidebar renders categories Electronics > Audio > Headphones
- **THEN** "Headphones" is nested two levels below "Electronics"

#### Scenario: Collapsed by default
- **WHEN** the home page loads with no category selected
- **THEN** only top-level categories and "All" are visible

#### Scenario: Expand control
- **WHEN** a user opens the "Electronics" disclosure
- **THEN** its direct subcategories become visible and no category is selected

#### Scenario: Select a parent category
- **WHEN** a user selects "Electronics"
- **THEN** "Electronics" is selected and products from all its product-holding subcategories are listed

#### Scenario: Selected category is revealed
- **WHEN** the page loads with "Headphones" selected
- **THEN** "Electronics" and "Audio" are open so "Headphones" is visible and marked

#### Scenario: Without JavaScript
- **WHEN** the page is shown with JavaScript disabled
- **THEN** every branch can still be opened and a category selected

### Requirement: Product page
Each product SHALL have a page at `/products/<slug>/` showing its picture, name, full category path, tags, price, stock, full description and Buy (when in stock). For logged-in users it SHALL also show a favourite control whose state is filled in by a separate asynchronous request for the user's favourite slugs, and which adds or removes the favourite without reloading the page. The page SHALL be accessible without logging in and SHALL show out-of-stock products too. Unknown slugs SHALL return 404.

#### Scenario: Open from a card
- **WHEN** a visitor clicks Details on the card of "Aurora ANC Headphones"
- **THEN** they see `/products/aurora-anc-headphones/` with that product's full description

#### Scenario: Favourite state from slugs
- **WHEN** a shopper whose favourite slugs include `aurora-anc-headphones` opens that page
- **THEN** the favourite control is shown as on once the slugs request completes

#### Scenario: Toggle without reload
- **WHEN** a shopper clicks the favourite control on a product page
- **THEN** the favourite is added or removed through an asynchronous request and the control and the navigation count update without a reload

#### Scenario: Anonymous favourite
- **WHEN** an anonymous visitor opens a product page
- **THEN** no favourite control is shown that works without login; a "Log in to favourite" link returns them to the page afterwards

#### Scenario: Actions return to the product page
- **WHEN** a logged-in shopper clicks Buy on a product page
- **THEN** the product page is shown again with the result message

#### Scenario: Out-of-stock product page
- **WHEN** a visitor opens the page of a product with stock 0
- **THEN** the page says "Out of stock" and has no Buy control

#### Scenario: Unknown slug
- **WHEN** a visitor opens `/products/no-such-product/`
- **THEN** the response is 404

### Requirement: My orders page
A logged-in user SHALL have a page listing their own orders, newest first, with items, quantities, prices paid and totals. Each order's time SHALL be shown in the viewer's local time.

#### Scenario: Order history
- **WHEN** a shopper who placed two orders opens My orders
- **THEN** both orders are listed with their items and totals, newest first

## REMOVED Requirements

### Requirement: Favourite toggle on cards
**Reason**: Favourite state is shown only on the product page; list pages carry no favourite flag.
**Migration**: Use the favourite control on the product page; the "Only my favourites" filter and My favourites page are unchanged.
