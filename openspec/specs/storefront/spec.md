# storefront Specification

## Purpose

Server-rendered shop pages for browsing, searching and filtering products, managing favourites, buying products and viewing past orders.

## Requirements

### Requirement: Product listing page
The storefront home page SHALL list products as cards showing name, full category path, tags, price, stock and, for logged-in users, favourite and Buy controls. It SHALL be accessible without logging in.

#### Scenario: Anonymous visitor
- **WHEN** an anonymous visitor opens the home page
- **THEN** in-stock products are listed and a Login link is shown instead of favourite and Buy controls

#### Scenario: Out-of-stock card
- **WHEN** out-of-stock products are included and shown
- **THEN** their cards say "Out of stock" and have no Buy control

### Requirement: Filter sidebar form
The sidebar SHALL be a single GET form containing a nested category radio tree, minimum and maximum price sliders, tag checkboxes with an ALL/ANY choice, an include-out-of-stock option, an only-favourites option for logged-in users, and Apply and Reset buttons.

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
The sidebar SHALL show every category as a tree indented by level, with an "All" option at the top. The selected category SHALL be marked.

#### Scenario: Tree rendering
- **WHEN** the sidebar renders categories Electronics > Audio > Headphones
- **THEN** "Headphones" is indented two levels below "Electronics"

### Requirement: Price sliders
The price sliders SHALL range from the lowest to the highest product price and SHALL show their current values. Filtering SHALL work without JavaScript.

#### Scenario: Slider bounds
- **WHEN** the cheapest product costs $5 and the most expensive $300
- **THEN** the sliders range from $5 to $300

### Requirement: Favourite toggle on cards
A logged-in user SHALL be able to add or remove a product from favourites from its card. The page SHALL then return to the same filtered view.

#### Scenario: Add favourite
- **WHEN** a logged-in shopper clicks the favourite control on an unfavourited product
- **THEN** the product becomes a favourite and the same filtered page is shown with the control marked

#### Scenario: Anonymous click
- **WHEN** an anonymous visitor tries to favourite a product
- **THEN** they are redirected to the login page and returned afterwards

### Requirement: One-click Buy
A logged-in user SHALL be able to buy one unit of an in-stock product from its card. The user SHALL see a success message or, if stock ran out, an out-of-stock message.

#### Scenario: Successful purchase
- **WHEN** a logged-in shopper clicks Buy on a product with stock 3
- **THEN** an order for 1 unit is created, stock becomes 2 and a success message is shown

#### Scenario: Sold out meanwhile
- **WHEN** a shopper clicks Buy after the last unit was sold
- **THEN** no order is created and an out-of-stock message is shown

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
