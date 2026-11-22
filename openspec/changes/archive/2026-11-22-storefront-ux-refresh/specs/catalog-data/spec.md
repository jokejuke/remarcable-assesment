# Spec Delta

## MODIFIED Requirements

### Requirement: Product attributes
Each product SHALL have a name, a slug, a description, a price in integer cents, a stock count (`items_available`), an optional picture address (`image_url`), exactly one category and any number of tags.

#### Scenario: Product created in the admin
- **WHEN** an administrator creates a product with name, description, price 4900 cents, stock 5, category "Headphones", tags "wireless" and "budget", and a picture address
- **THEN** the product is saved with all of these values and a slug

#### Scenario: Product without picture
- **WHEN** an administrator saves a product with an empty picture address
- **THEN** the product is saved with no picture

### Requirement: Catalog is managed in the admin
Administrators SHALL be able to create, edit and delete categories, tags and products through the Django admin, including each product's slug and picture address. Orders SHALL be view-only in the admin.

#### Scenario: Admin product list
- **WHEN** an administrator opens the product list in the admin
- **THEN** products are listed with name, category, price, stock and can be filtered by category and tags and searched by name

#### Scenario: Orders view-only
- **WHEN** an administrator opens an order in the admin
- **THEN** its fields and items are shown but cannot be edited, added or deleted

#### Scenario: Slug and picture editable
- **WHEN** an administrator opens a product in the admin
- **THEN** its slug and picture address can be edited

## ADDED Requirements

### Requirement: Product slugs are unique and stable
Each product SHALL have a URL slug of lower-case letters, digits and hyphens, unique across all products. When a product is created without a slug, the slug SHALL be generated from its name, adding a numeric suffix if needed to stay unique. Renaming a product SHALL NOT change its slug.

#### Scenario: Generated slug
- **WHEN** a product named "Aurora ANC Headphones" is created without a slug
- **THEN** its slug is `aurora-anc-headphones`

#### Scenario: Colliding slug
- **WHEN** a product named "C++ Primer" is created while a product with slug `c-primer` exists
- **THEN** the new product gets slug `c-primer-2`

#### Scenario: Rename keeps slug
- **WHEN** an administrator renames "Aurora ANC Headphones" to "Aurora ANC Headphones II"
- **THEN** its slug stays `aurora-anc-headphones`

#### Scenario: Duplicate slug entered by hand
- **WHEN** an administrator sets a product's slug to one another product already uses
- **THEN** the save is rejected with a uniqueness error

### Requirement: Picture address is a web URL
A product's `image_url` SHALL be empty or an absolute `http` or `https` URL.

#### Scenario: Invalid picture address
- **WHEN** an administrator saves a product with picture address `javascript:alert(1)`
- **THEN** validation fails with an error on the picture field
