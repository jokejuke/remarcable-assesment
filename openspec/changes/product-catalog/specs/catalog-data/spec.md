# Spec Delta

## Purpose

Defines the products and tags in the catalog, including their fields, relationships and constraints, and how administrators manage them through the Django admin.

## ADDED Requirements

### Requirement: Product attributes
Each product SHALL have a name, a description, a price in integer cents, a stock count (`items_available`), exactly one category and any number of tags.

#### Scenario: Product created in the admin
- **WHEN** an administrator creates a product with name, description, price 4900 cents, stock 5, category "Headphones" and tags "wireless" and "budget"
- **THEN** the product is saved with all of these values

### Requirement: Product and tag names are unique
Product names SHALL be unique across all products, and tag names SHALL be unique across all tags.

#### Scenario: Duplicate product name
- **WHEN** an administrator creates a product whose name already exists
- **THEN** the save is rejected with a uniqueness error

#### Scenario: Duplicate tag name
- **WHEN** an administrator creates a tag whose name already exists
- **THEN** the save is rejected with a uniqueness error

### Requirement: Price is stored in cents
Prices SHALL be stored as non-negative whole numbers of cents in a single currency, and displayed as a currency amount with two decimals.

#### Scenario: Price display
- **WHEN** a product priced at 4900 cents is displayed
- **THEN** it shows as "$49.00"

#### Scenario: Negative price
- **WHEN** a product is saved with a negative price
- **THEN** the save is rejected

### Requirement: Stock is never negative
`items_available` SHALL be a non-negative integer, enforced by the database.

#### Scenario: Negative stock
- **WHEN** any write would set a product's stock below zero
- **THEN** the write is rejected

### Requirement: Products only in product-holding categories
A product's category SHALL be one marked as holding products. The admin SHALL offer only such categories.

#### Scenario: Assigning a subcategory-holding category
- **WHEN** a product is validated with category "Electronics", which holds subcategories
- **THEN** validation fails with an error on the category field

#### Scenario: Admin choices
- **WHEN** an administrator opens the product form
- **THEN** the category choices include only categories that hold products

### Requirement: Timestamps in Unix seconds
Every catalog table (categories, tags, products, favourites, orders and order items) SHALL record `created_at` when a row is created and `updated_at` whenever it changes, as whole Unix seconds.

#### Scenario: Category edited
- **WHEN** an administrator renames a category created earlier
- **THEN** its `created_at` is unchanged and its `updated_at` is the current Unix time in seconds

#### Scenario: New row
- **WHEN** a favourite is created
- **THEN** its `created_at` and `updated_at` are both the current Unix time in seconds

#### Scenario: Product edited
- **WHEN** an administrator edits a product created earlier
- **THEN** `created_at` is unchanged and `updated_at` is the current Unix time in seconds

#### Scenario: Stock decremented by checkout
- **WHEN** a checkout reduces a product's stock
- **THEN** the product's `updated_at` is set to the time of the checkout

### Requirement: Tags can be removed without losing products
Deleting a tag SHALL remove it from all products and leave the products intact.

#### Scenario: Tag deleted
- **WHEN** an administrator deletes the tag "budget"
- **THEN** products previously tagged "budget" still exist without that tag

### Requirement: Products with orders are protected
A product that appears in any order SHALL NOT be deletable.

#### Scenario: Deleting an ordered product
- **WHEN** an administrator deletes a product that has been ordered
- **THEN** the deletion is refused

### Requirement: Catalog is managed in the admin
Administrators SHALL be able to create, edit and delete categories, tags and products through the Django admin. Orders SHALL be view-only in the admin.

#### Scenario: Admin product list
- **WHEN** an administrator opens the product list in the admin
- **THEN** products are listed with name, category, price, stock and can be filtered by category and tags and searched by name

#### Scenario: Orders view-only
- **WHEN** an administrator opens an order in the admin
- **THEN** its fields and items are shown but cannot be edited, added or deleted
