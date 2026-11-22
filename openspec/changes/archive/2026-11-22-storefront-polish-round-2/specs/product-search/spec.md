## MODIFIED Requirements

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
