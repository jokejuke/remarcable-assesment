# demo-data Specification

## Purpose

Provides repeatable sample data and demo accounts, so a reviewer who clones the repository can explore every feature right away without entering data by hand.

## Requirements

### Requirement: Catalog fixture
The repository SHALL include a catalog fixture with at least 5 categories, 10 tags and 20 products. The data SHALL be exported from a database with `dumpdata`, not written by hand.

#### Scenario: Loading the catalog
- **WHEN** a reviewer loads the catalog fixture into a freshly migrated database
- **THEN** the database contains at least 5 categories, 10 tags and 20 products

### Requirement: Fixture covers every feature
The catalog fixture SHALL include a category tree three levels deep in which at least one category can be expanded to show a further expandable category, products with several tags each, a range of prices, at least one out-of-stock product, products with pictures, and at least one product without a picture. It SHALL hold more products than fit on one storefront page.

#### Scenario: Three-level tree
- **WHEN** the catalog fixture is loaded
- **THEN** at least one category exists at level 3 with products in it

#### Scenario: Out-of-stock sample
- **WHEN** the catalog fixture is loaded and the default listing is shown
- **THEN** at least one product is hidden because its stock is 0

#### Scenario: Pictures and placeholder
- **WHEN** the catalog fixture is loaded
- **THEN** most products have a picture address and at least one has none

#### Scenario: Several pages
- **WHEN** the catalog fixture is loaded and all products are included
- **THEN** the storefront listing has more than one page

### Requirement: Fixture data satisfies all rules
Every record in the fixtures SHALL satisfy the category, product and tag rules, even though fixture loading skips form validation.

#### Scenario: Validation pass
- **WHEN** the full model validation is run over every loaded fixture record
- **THEN** no validation errors are reported

### Requirement: Demo users fixture
A separate users fixture SHALL provide one superuser for the admin and two regular shoppers without admin access. All demo accounts SHALL use their email address as the username. The first shopper SHALL have a few favourite products and the second shopper none. Passwords SHALL be stored only as hashes.

#### Scenario: Admin login
- **WHEN** the demo admin logs in to `/admin/` as `admin@example.com`
- **THEN** they can manage categories, tags and products

#### Scenario: Shopper has no admin access
- **WHEN** either demo shopper tries to open `/admin/`
- **THEN** access is denied

#### Scenario: Shopper favourites present
- **WHEN** `shopper@example.com` opens My favourites after loading the fixtures
- **THEN** at least two favourites are listed

#### Scenario: Second shopper starts empty
- **WHEN** `shopper2@example.com` opens My favourites after loading the fixtures
- **THEN** no favourites are listed

### Requirement: Demo data is clearly separated
The demo users fixture SHALL be a separate file from the catalog fixture. The documentation SHALL list the demo credentials and warn that the users fixture must never be loaded in production.

#### Scenario: Catalog only
- **WHEN** only the catalog fixture is loaded
- **THEN** no user accounts are created

### Requirement: Demo category tree
The catalog fixture SHALL contain exactly these 7 categories, holding all 25 products: Books; Electronics, containing Audio (with Headphones and Speakers) and Computers & Phones; and Home & Outdoors.

#### Scenario: Category set
- **WHEN** the catalog fixture is loaded
- **THEN** the category paths are "Books", "Electronics", "Electronics > Audio", "Electronics > Audio > Headphones", "Electronics > Audio > Speakers", "Electronics > Computers & Phones" and "Home & Outdoors"

#### Scenario: Every product kept
- **WHEN** the catalog fixture is loaded
- **THEN** it contains 25 products, each in a category that holds products

### Requirement: Demo products have pictures
Every product in the catalog fixture SHALL have an absolute `http` or `https` picture URL. The fixture SHALL NOT embed image files.

#### Scenario: No product without a picture
- **WHEN** the catalog fixture is loaded
- **THEN** every product has a non-empty `image_url`

#### Scenario: Pictures are links only
- **WHEN** the repository is inspected
- **THEN** no product image files are stored in it
