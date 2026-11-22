# demo-data Specification

## Purpose

Provides repeatable sample data and demo accounts, so a reviewer who clones the repository can explore every feature right away without entering data by hand.

## Requirements

### Requirement: Catalog fixture
The repository SHALL include a catalog fixture with at least 5 categories, 10 tags and 20 products. The data SHALL be entered through the Django admin and then exported.

#### Scenario: Loading the catalog
- **WHEN** a reviewer loads the catalog fixture into a freshly migrated database
- **THEN** the database contains at least 5 categories, 10 tags and 20 products

### Requirement: Fixture covers every feature
The catalog fixture SHALL include a category tree three levels deep, products with several tags each, a range of prices, and at least one out-of-stock product.

#### Scenario: Three-level tree
- **WHEN** the catalog fixture is loaded
- **THEN** at least one category exists at level 3 with products in it

#### Scenario: Out-of-stock sample
- **WHEN** the catalog fixture is loaded and the default listing is shown
- **THEN** at least one product is hidden because its stock is 0

### Requirement: Fixture data satisfies all rules
Every record in the fixtures SHALL satisfy the category, product and tag rules, even though fixture loading skips form validation.

#### Scenario: Validation pass
- **WHEN** the full model validation is run over every loaded fixture record
- **THEN** no validation errors are reported

### Requirement: Demo users fixture
A separate users fixture SHALL provide one superuser for the admin and one regular shopper without admin access. The shopper SHALL have a few favourite products. Passwords SHALL be stored only as hashes.

#### Scenario: Admin login
- **WHEN** the demo admin logs in to `/admin/`
- **THEN** they can manage categories, tags and products

#### Scenario: Shopper has no admin access
- **WHEN** the demo shopper tries to open `/admin/`
- **THEN** access is denied

#### Scenario: Shopper favourites present
- **WHEN** the demo shopper opens My favourites after loading the fixtures
- **THEN** at least two favourites are listed

### Requirement: Demo data is clearly separated
The demo users fixture SHALL be a separate file from the catalog fixture. The documentation SHALL list the demo credentials and warn that the users fixture must never be loaded in production.

#### Scenario: Catalog only
- **WHEN** only the catalog fixture is loaded
- **THEN** no user accounts are created
