# product-search Specification

## Purpose

Defines how products are searched and filtered, and how the filters combine. The storefront and the API share these rules, so the same parameters give the same results in both.

## Requirements

### Requirement: Text search with all words required
The search text SHALL be split into words. A product SHALL match only if every word appears, case-insensitively, in its name or description. Empty search text SHALL apply no text filter.

#### Scenario: All words present
- **WHEN** a user searches "wireless noise" and a product's description contains "noise-cancelling wireless headphones"
- **THEN** the product is in the results

#### Scenario: One word missing
- **WHEN** a user searches "wireless bluetooth" and a product mentions "wireless" but not "bluetooth"
- **THEN** the product is not in the results

#### Scenario: Word in name only
- **WHEN** a user searches "earbuds" and only the product name contains "Earbuds"
- **THEN** the product is in the results

### Requirement: Filter by one category including descendants
A query SHALL accept at most one category. Results SHALL include products in that category and in every category below it. The query SHALL only match categories with `has_products = true`: for a category that holds subcategories, the matching set is its descendants that hold products; a product-holding category with no products SHALL simply return no results.

#### Scenario: Top-level category
- **WHEN** a user filters by "Electronics"
- **THEN** products in "Headphones", "Speakers" and "Computers" are all returned

#### Scenario: Leaf category
- **WHEN** a user filters by "Headphones"
- **THEN** only products in "Headphones" are returned

#### Scenario: Only product-holding categories queried
- **WHEN** a user filters by a category that holds subcategories
- **THEN** the product query's category condition lists only descendant categories with `has_products = true`, never the parent or other non-product categories

#### Scenario: Unknown category
- **WHEN** a request filters by a category id that does not exist
- **THEN** the storefront shows a form error and the API responds 400

### Requirement: Filter by tags with ALL or ANY matching
A query SHALL accept any number of tags and a match mode. In ALL mode, the default, products SHALL have every selected tag. In ANY mode, products SHALL have at least one. Each product SHALL appear once.

#### Scenario: ALL mode
- **WHEN** a user selects tags "wireless" and "budget" with match mode ALL
- **THEN** only products tagged with both are returned

#### Scenario: ANY mode
- **WHEN** a user selects tags "wireless" and "budget" with match mode ANY
- **THEN** products tagged with either are returned, each exactly once

#### Scenario: Default mode
- **WHEN** a user selects two tags without choosing a match mode
- **THEN** ALL matching is applied

### Requirement: Filter by price range
A query SHALL accept an optional minimum and maximum price, each inclusive. A minimum greater than the maximum SHALL be rejected as invalid input.

#### Scenario: Price range
- **WHEN** a user filters with minimum $20 and maximum $150
- **THEN** only products priced from 2000 to 15000 cents inclusive are returned

#### Scenario: Inverted range
- **WHEN** a request sets the minimum above the maximum
- **THEN** the storefront shows a form error and the API responds 400

### Requirement: Out-of-stock products hidden by default
Products with zero stock SHALL be excluded unless the query asks to include out-of-stock products.

#### Scenario: Default listing
- **WHEN** a user loads the product list without stock options
- **THEN** products with `items_available` = 0 are not shown

#### Scenario: Include out of stock
- **WHEN** a user enables "include out of stock"
- **THEN** products with zero stock are also returned

### Requirement: Only-favourites filter
An authenticated user SHALL be able to restrict results to their own favourites. Anonymous users SHALL NOT be able to use this filter.

#### Scenario: Shopper filters favourites
- **WHEN** a logged-in shopper enables "only favourites"
- **THEN** only products the shopper has favourited are returned

#### Scenario: Anonymous request
- **WHEN** an anonymous request asks for only favourites
- **THEN** the filter is ignored on the storefront and the API responds 401

### Requirement: Filters combine with AND
Search, category, tags, price, stock and favourites filters SHALL combine so a product must satisfy every active filter. With no filters, all in-stock products SHALL be returned.

#### Scenario: Combined filters
- **WHEN** a user searches "wireless", picks category "Audio", tags "budget" (ALL) and maximum price $100
- **THEN** only in-stock products in "Audio" or below, matching "wireless", tagged "budget" and priced at most 10000 cents are returned

### Requirement: Results are ordered and paginated
Results SHALL be ordered by name by default and paginated. The storefront and the API SHALL keep the active filters when moving between pages.

#### Scenario: Next page keeps filters
- **WHEN** a user on page 1 of a filtered list goes to page 2
- **THEN** page 2 applies the same filters

### Requirement: Same parameters in storefront and API
The storefront and the product list API SHALL accept the same filter parameter names and SHALL return the same set of products for the same parameters.

#### Scenario: Parity
- **WHEN** the same query string is sent to the storefront and to the product list API
- **THEN** both return the same products in the same order

### Requirement: Bounded query count
Listing a page of products, including categories, tags and favourite state, SHALL use a fixed number of database queries regardless of how many products are on the page.

#### Scenario: Larger page
- **WHEN** a page of 5 products and a page of 20 products are listed with the same filters
- **THEN** both use the same number of queries
