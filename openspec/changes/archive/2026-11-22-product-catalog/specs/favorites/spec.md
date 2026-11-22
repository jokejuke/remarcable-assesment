# Spec Delta

## Purpose

Lets logged-in users keep a private list of favourite products and manage it from both the storefront and the API.

## ADDED Requirements

### Requirement: Favourites belong to one user
Each favourite SHALL link one user to one product, at most once per pair. Users SHALL only ever see and change their own favourites.

#### Scenario: Private list
- **WHEN** shopper A lists favourites
- **THEN** none of shopper B's favourites are included

### Requirement: Adding a favourite can be repeated safely
Adding a product that is already a favourite SHALL succeed without creating a duplicate.

#### Scenario: Add twice
- **WHEN** a shopper adds the same product to favourites twice
- **THEN** exactly one favourite exists for that product

### Requirement: Removing a favourite can be repeated safely
Removing a product that is not a favourite SHALL succeed without error.

#### Scenario: Remove non-favourite
- **WHEN** a shopper removes a product that is not in their favourites
- **THEN** the request succeeds and nothing changes

### Requirement: Favourites require login
Anonymous users SHALL NOT be able to read or change favourites.

#### Scenario: Anonymous API request
- **WHEN** an unauthenticated client calls the favourites API
- **THEN** it receives 401

### Requirement: Favourite state on products
When a logged-in user lists products, each product SHALL indicate whether it is in that user's favourites.

#### Scenario: Product flag
- **WHEN** a shopper who favourited product 7 lists products
- **THEN** product 7 is marked as a favourite and others are not

### Requirement: Favourites follow their product and user
Deleting a product or a user SHALL delete the related favourites.

#### Scenario: User removed
- **WHEN** an administrator deletes a user who had favourites
- **THEN** those favourites no longer exist
