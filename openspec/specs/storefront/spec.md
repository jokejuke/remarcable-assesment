# storefront Specification

## Purpose

Server-rendered shop pages for browsing, searching and filtering products, managing favourites, buying products and viewing past orders.

## Requirements

### Requirement: Product listing page
The storefront home page SHALL list products as cards showing picture, name, full category path, tags, price, stock, a Details link to the product page and, for in-stock products, a Buy control. Logged-in users SHALL also see a favourite control. It SHALL be accessible without logging in.

#### Scenario: Anonymous visitor
- **WHEN** an anonymous visitor opens the home page
- **THEN** in-stock products are listed, each card shows Details and Buy, and no favourite control is shown

#### Scenario: Logged-in visitor
- **WHEN** a logged-in shopper opens the home page
- **THEN** each in-stock card shows Details, Buy and a favourite control

#### Scenario: Out-of-stock card
- **WHEN** out-of-stock products are included and shown
- **THEN** their cards say "Out of stock", show Details and have no Buy control

### Requirement: Filter sidebar form
The sidebar SHALL be a single GET form containing a collapsible category radio tree, a price range control, tag checkboxes with an ALL/ANY choice, an include-out-of-stock option, an only-favourites option for logged-in users, and Apply and Reset buttons.

#### Scenario: Apply filters
- **WHEN** a user selects "Headphones", tags "wireless" and "budget", and clicks Apply
- **THEN** the page reloads with those filters in the URL and the matching products

#### Scenario: Reset
- **WHEN** a user clicks Reset
- **THEN** all filters are cleared and the default listing is shown

#### Scenario: Form keeps state
- **WHEN** the page loads from a URL with filters
- **THEN** the sidebar controls show those filter values as selected

### Requirement: Search bar
The header SHALL contain a search input whose value is submitted together with the sidebar filters.

#### Scenario: Search with filters
- **WHEN** a user has category "Audio" selected and searches "wireless"
- **THEN** results match "wireless" within "Audio"

### Requirement: Nested category tree in the sidebar
The sidebar SHALL show categories as a tree indented by level, with an "All" option at the top. The selected category SHALL be marked. Categories that have subcategories SHALL be collapsed by default and SHALL have a separate expand control; clicking a category's name SHALL select it without expanding or collapsing it. Without JavaScript the whole tree SHALL be shown expanded.

#### Scenario: Tree rendering
- **WHEN** the sidebar renders categories Electronics > Audio > Headphones
- **THEN** "Headphones" is indented two levels below "Electronics"

#### Scenario: Collapsed by default
- **WHEN** the home page loads with no category selected
- **THEN** only top-level categories and "All" are visible

#### Scenario: Expand control
- **WHEN** a user clicks the expand control next to "Electronics"
- **THEN** its direct subcategories become visible and no category is selected

#### Scenario: Select a parent category
- **WHEN** a user clicks the name "Electronics"
- **THEN** "Electronics" is selected and its subcategories stay as they were

#### Scenario: Selected category is revealed
- **WHEN** the page loads with "Headphones" selected
- **THEN** "Electronics" and "Audio" are expanded so "Headphones" is visible and marked

#### Scenario: Without JavaScript
- **WHEN** the page is shown with JavaScript disabled
- **THEN** every category is visible

### Requirement: Price sliders
The price filter SHALL be a single track with a minimum and a maximum handle, ranging from the lowest to the highest product price and showing both current values. The minimum handle SHALL NOT pass the maximum handle. Without JavaScript it SHALL fall back to two separate sliders, and filtering SHALL still work.

#### Scenario: Slider bounds
- **WHEN** the cheapest product costs $5 and the most expensive $300
- **THEN** the track ranges from $5 to $300

#### Scenario: Handles cannot cross
- **WHEN** a user drags the minimum handle past the maximum handle
- **THEN** both handles stay at the same value and the labels show it

#### Scenario: Without JavaScript
- **WHEN** the page is shown with JavaScript disabled
- **THEN** two separate minimum and maximum sliders are shown and Apply filters by them

### Requirement: Favourite toggle on cards
A logged-in user SHALL be able to add or remove a product from favourites from its card. The page SHALL then return to the same filtered view.

#### Scenario: Add favourite
- **WHEN** a logged-in shopper clicks the favourite control on an unfavourited product
- **THEN** the product becomes a favourite and the same filtered page is shown with the control marked

#### Scenario: Anonymous click
- **WHEN** an anonymous visitor tries to favourite a product
- **THEN** they are redirected to the login page and returned afterwards

### Requirement: One-click Buy
A logged-in user SHALL be able to buy one unit of an in-stock product from its card or its product page. The user SHALL see a success message or, if stock ran out, an out-of-stock message. An anonymous visitor who clicks Buy SHALL be sent to the login page and, after logging in or signing up, returned to the page they came from without any order being placed.

#### Scenario: Successful purchase
- **WHEN** a logged-in shopper clicks Buy on a product with stock 3
- **THEN** an order for 1 unit is created, stock becomes 2 and a success message is shown

#### Scenario: Sold out meanwhile
- **WHEN** a shopper clicks Buy after the last unit was sold
- **THEN** no order is created and an out-of-stock message is shown

#### Scenario: Anonymous Buy
- **WHEN** an anonymous visitor clicks Buy on a filtered listing page and then logs in
- **THEN** they are returned to the same filtered listing page, no order exists and stock is unchanged

### Requirement: My favourites page
A logged-in user SHALL have a page listing their favourite products, including out-of-stock ones marked as such.

#### Scenario: Favourites list
- **WHEN** a shopper with three favourites, one out of stock, opens My favourites
- **THEN** all three are listed and the out-of-stock one is marked

### Requirement: My orders page
A logged-in user SHALL have a page listing their own orders, newest first, with items, quantities, prices paid and totals.

#### Scenario: Order history
- **WHEN** a shopper who placed two orders opens My orders
- **THEN** both orders are listed with their items and totals, newest first

### Requirement: Login and logout
The storefront SHALL provide login and logout pages, and show the logged-in username in the header.

#### Scenario: Login
- **WHEN** the shopper logs in with valid credentials
- **THEN** they return to the page they came from and the header shows their username

### Requirement: Safe redirects
Any redirect target taken from request parameters SHALL be limited to this site. Other targets SHALL fall back to the home page.

#### Scenario: External redirect target
- **WHEN** a favourite or Buy request carries `next=https://evil.example`
- **THEN** the user is redirected to the home page instead

### Requirement: Product page
Each product SHALL have a page at `/products/<slug>/` showing its picture, name, full category path, tags, price, stock, full description, Buy (when in stock) and, for logged-in users, the favourite control. The page SHALL be accessible without logging in and SHALL show out-of-stock products too. Unknown slugs SHALL return 404.

#### Scenario: Open from a card
- **WHEN** a visitor clicks Details on the card of "Aurora ANC Headphones"
- **THEN** they see `/products/aurora-anc-headphones/` with that product's full description

#### Scenario: Out-of-stock product page
- **WHEN** a visitor opens the page of a product with stock 0
- **THEN** the page says "Out of stock" and has no Buy control

#### Scenario: Unknown slug
- **WHEN** a visitor opens `/products/no-such-product/`
- **THEN** the response is 404

#### Scenario: Actions return to the product page
- **WHEN** a logged-in shopper clicks Buy or the favourite control on a product page
- **THEN** the product page is shown again with the result message

### Requirement: Product pictures
Cards and product pages SHALL show the product's picture. When a product has no picture, or its picture fails to load, a neutral placeholder of the same size SHALL be shown instead. Every picture SHALL have the product name as its text alternative.

#### Scenario: Product without picture
- **WHEN** a product with no picture is listed
- **THEN** its card shows the placeholder

#### Scenario: Broken picture link
- **WHEN** a product's picture address cannot be loaded
- **THEN** the placeholder is shown in its place

### Requirement: Apply reflects pending changes
The Apply button SHALL be disabled while the filter controls match the filters of the current page, and SHALL become enabled as soon as any filter control or the search field changes. Changing a control back to its original value SHALL disable Apply again. Without JavaScript Apply SHALL always be enabled.

#### Scenario: Fresh page
- **WHEN** the listing page loads
- **THEN** Apply is disabled

#### Scenario: A filter changes
- **WHEN** a user ticks the tag "wireless"
- **THEN** Apply becomes enabled

#### Scenario: Change undone
- **WHEN** the user unticks "wireless" again
- **THEN** Apply is disabled again

### Requirement: Reset reflects applied filters
The Reset control SHALL be disabled when the current page applies no filter beyond the defaults, and enabled otherwise. A price range equal to the full slider range, ALL tag matching and an empty search SHALL count as defaults.

#### Scenario: Default listing
- **WHEN** the home page is opened without filters
- **THEN** Reset is disabled

#### Scenario: Filtered listing
- **WHEN** the page is opened with a category filter
- **THEN** Reset is enabled

#### Scenario: Full price range only
- **WHEN** the page is opened with only `price_min` and `price_max` equal to the slider bounds
- **THEN** Reset is disabled

### Requirement: Filter actions always visible
Apply and Reset SHALL stay visible at all times while the listing page is scrolled. On wide screens they SHALL sit at the bottom of the sidebar, and the sidebar's filters SHALL scroll above them when they do not fit. On narrow screens they SHALL sit in a bar fixed to the bottom of the screen that does not cover the last products.

#### Scenario: Long sidebar on desktop
- **WHEN** a desktop user scrolls the listing to the bottom of a long page
- **THEN** Apply and Reset are visible at the bottom of the sidebar

#### Scenario: Narrow screen
- **WHEN** the listing is shown on a 375px-wide screen and scrolled
- **THEN** Apply and Reset stay in a bar at the bottom of the screen

#### Scenario: Last product reachable on narrow screen
- **WHEN** a user on a narrow screen scrolls to the end of the listing
- **THEN** the last product and the pagination links are not covered by the bar

### Requirement: Listing page size
The storefront listing SHALL show 10 products per page.

#### Scenario: 25 matching products
- **WHEN** 25 products match the filters
- **THEN** the listing has 3 pages with 10, 10 and 5 products
