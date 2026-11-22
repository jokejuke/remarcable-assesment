# Spec Delta

## Purpose

A JSON API under `/api/` that exposes the catalog read-only and lets authenticated users manage their favourites and orders. It is documented with an OpenAPI 3 schema and an interactive Swagger UI.

## ADDED Requirements

### Requirement: Read-only catalog endpoints
The API SHALL expose list and detail endpoints for products, categories and tags. It SHALL NOT accept create, update or delete requests for them. These endpoints SHALL be readable without authentication.

#### Scenario: List products anonymously
- **WHEN** an anonymous client sends GET `/api/products/`
- **THEN** it receives 200 with a paginated list of products

#### Scenario: Write attempt
- **WHEN** any client sends POST, PUT, PATCH or DELETE to `/api/products/`, `/api/categories/` or `/api/tags/`
- **THEN** it receives 405 (or 401 if unauthenticated) and nothing changes

### Requirement: Product representation
Each product in API responses SHALL include id, name, description, `price_cents`, a formatted price, `items_available`, category (id, name, full path), tags (id, name), and `created_at`/`updated_at` in Unix seconds. For authenticated users it SHALL include `is_favorite`.

#### Scenario: Authenticated product detail
- **WHEN** a logged-in shopper requests a product they favourited
- **THEN** the response includes `"is_favorite": true` with the fields above

### Requirement: Product list filters
The product list endpoint SHALL support every filter defined by product search, using the same parameter names as the storefront.

#### Scenario: Filtered list
- **WHEN** a client requests `/api/products/?q=wireless&category=3&tags=1&tags=4&match=any`
- **THEN** the response contains the products defined by product search for those parameters

### Requirement: Category endpoint shows the tree
Category responses SHALL include id, name, parent id, full path, and whether the category holds products or subcategories.

#### Scenario: Category list
- **WHEN** a client requests `/api/categories/`
- **THEN** every category is returned with its parent id and full path

### Requirement: Favourites endpoints
Authenticated users SHALL be able to list their favourites, add one by product id, and remove one by product id.

#### Scenario: Add favourite
- **WHEN** a shopper sends POST `/api/favorites/` with `{"product": 7}`
- **THEN** the response is 201, or 200 if it already existed, and product 7 is a favourite

#### Scenario: Remove favourite
- **WHEN** a shopper sends DELETE `/api/favorites/7/`
- **THEN** the response is 204 whether or not it was a favourite

#### Scenario: Unknown product
- **WHEN** a shopper adds a favourite for a product id that does not exist
- **THEN** the response is 400

### Requirement: Orders endpoints
Authenticated users SHALL be able to place an order with POST `/api/orders/`, and list and view their own orders.

#### Scenario: Place order
- **WHEN** a shopper sends POST `/api/orders/` with `{"items": [{"product": 7, "quantity": 2}]}` and stock allows it
- **THEN** the response is 201 with the order, its items and total

### Requirement: Consistent error format
Validation and business errors SHALL return JSON bodies with appropriate status codes (400, 401, 404, 405, 409). Error bodies SHALL NOT expose stack traces.

#### Scenario: Invalid filter
- **WHEN** a client requests `/api/products/?category=abc`
- **THEN** the response is 400 with a JSON body naming the `category` field

### Requirement: OpenAPI schema and Swagger UI
The API SHALL publish an OpenAPI 3 schema at `/api/schema/` and an interactive Swagger UI at `/api/docs/`. The schema SHALL describe every endpoint, its filter parameters, request and response bodies, and the authentication methods.

#### Scenario: Schema download
- **WHEN** a client requests `/api/schema/`
- **THEN** it receives a valid OpenAPI 3 document that includes the product filter parameters

#### Scenario: Try it out with a token
- **WHEN** a user authorizes Swagger UI with a valid access token and calls GET `/api/favorites/`
- **THEN** the call succeeds and shows their favourites
