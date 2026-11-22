# Spec Delta

## MODIFIED Requirements

### Requirement: Product representation
Each product in API responses SHALL include id, slug, name, description, `price_cents`, a formatted price, `items_available`, `image_url` (an empty string when the product has no picture), category (id, name, full path), tags (id, name), and `created_at`/`updated_at` in Unix seconds. List and detail responses SHALL use the same representation. For authenticated users it SHALL include `is_favorite`.

#### Scenario: Authenticated product detail
- **WHEN** a logged-in shopper requests a product they favourited
- **THEN** the response includes `"is_favorite": true` with the fields above

#### Scenario: Picture and slug in the list
- **WHEN** a client requests `/api/products/`
- **THEN** every product in the list includes `slug` and `image_url`

#### Scenario: Product without picture
- **WHEN** a client requests a product that has no picture
- **THEN** its `image_url` is `""`
