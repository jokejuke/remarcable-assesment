# category-hierarchy Specification

## Purpose

Organises products into a tree of categories with a configurable maximum depth. Categories that hold products are kept separate from categories that hold subcategories, and the tree stays valid and quick to read.

## Requirements

### Requirement: Categories form a tree
Each category SHALL have at most one parent category. A category without a parent is a top-level category. A category can have any number of child categories.

#### Scenario: Top-level category
- **WHEN** an administrator creates a category without a parent
- **THEN** the category is saved as a top-level category

#### Scenario: Child category
- **WHEN** an administrator creates "Audio" with parent "Electronics"
- **THEN** "Audio" appears as a child of "Electronics"

### Requirement: Category names are unique
Category names SHALL be unique across the whole catalog, regardless of their position in the tree.

#### Scenario: Duplicate name under a different parent
- **WHEN** an administrator creates a category named "Audio" while another category named "Audio" exists under a different parent
- **THEN** the save is rejected with a uniqueness error

### Requirement: A category holds either products or subcategories
Each category SHALL be marked as holding products or as holding subcategories, with exactly one of the two set. The rule SHALL be enforced by the database as well as by form validation.

#### Scenario: Both kinds selected
- **WHEN** a category is saved marked as holding both products and subcategories
- **THEN** the save is rejected

#### Scenario: Neither kind selected
- **WHEN** a category is saved marked as holding neither products nor subcategories
- **THEN** the save is rejected

### Requirement: Parent must hold subcategories
A category's parent SHALL be a category marked as holding subcategories.

#### Scenario: Parent holds products
- **WHEN** an administrator sets the parent of a category to a category that holds products
- **THEN** validation fails with an error on the parent field

### Requirement: Category kind cannot change while in use
A category marked as holding products SHALL NOT be switched to holding subcategories while it has products. A category marked as holding subcategories SHALL NOT be switched to holding products while it has child categories.

#### Scenario: Switching a category that has products
- **WHEN** an administrator switches "Headphones", which has products, to hold subcategories
- **THEN** validation fails and the category is unchanged

#### Scenario: Switching a category that has children
- **WHEN** an administrator switches "Audio", which has child categories, to hold products
- **THEN** validation fails and the category is unchanged

### Requirement: Maximum tree depth is configurable
The tree SHALL NOT be deeper than the configured maximum depth, counting the top level as level 1. The default maximum depth SHALL be 3.

#### Scenario: Creating a category below the limit
- **WHEN** the maximum depth is 3 and an administrator creates a category under a level-2 category
- **THEN** the category is saved at level 3

#### Scenario: Creating a category beyond the limit
- **WHEN** the maximum depth is 3 and an administrator creates a category under a level-3 category
- **THEN** validation fails with a depth error

#### Scenario: Moving a subtree beyond the limit
- **WHEN** the maximum depth is 3 and an administrator moves a level-1 category that has children under another level-1 category
- **THEN** validation fails because its children would end up at level 4

#### Scenario: Different configured depth
- **WHEN** the maximum depth is configured as 2
- **THEN** a category can be created at level 2 but not at level 3

### Requirement: Deepest level holds products
A category at the maximum depth SHALL be marked as holding products.

#### Scenario: Container at the deepest level
- **WHEN** the maximum depth is 3 and an administrator creates a level-3 category marked as holding subcategories
- **THEN** validation fails

### Requirement: No loops in the tree
The system SHALL reject any change that makes a category its own ancestor.

#### Scenario: Category as its own parent
- **WHEN** an administrator sets a category's parent to itself
- **THEN** validation fails with a loop error

#### Scenario: Category under its own descendant
- **WHEN** an administrator sets the parent of "Electronics" to "Headphones", which is a descendant of "Electronics"
- **THEN** validation fails with a loop error and the tree is unchanged

### Requirement: Categories in use cannot be deleted
A category that has child categories or products SHALL NOT be deletable.

#### Scenario: Deleting a category with products
- **WHEN** an administrator deletes a category that still has products
- **THEN** the deletion is refused and the related objects are listed

#### Scenario: Deleting an empty category
- **WHEN** an administrator deletes a category with no children and no products
- **THEN** the category is deleted

### Requirement: Category tree reads are cached
The category tree used for navigation, full-path labels and descendant lookups SHALL be served from a cache. Writes and validation SHALL always read from the database.

#### Scenario: Repeated page loads
- **WHEN** the storefront is loaded twice and no category changed in between
- **THEN** the second load runs no database query for the category tree

### Requirement: Category cache is invalidated on change
Saving or deleting a category SHALL invalidate the cached tree once the change is committed, so the next read reflects it. Cached entries SHALL also expire after a bounded time.

#### Scenario: Rename is visible on the next request
- **WHEN** an administrator renames "Audio" to "Sound" and the storefront is reloaded
- **THEN** the sidebar shows "Sound"

#### Scenario: Rolled-back change keeps the cache
- **WHEN** a category save is rolled back
- **THEN** the cache is not invalidated

### Requirement: Full category path labels
The system SHALL present each category with its full path from the top level, for example "Electronics > Audio > Headphones".

#### Scenario: Leaf category label
- **WHEN** a product in "Headphones" is shown
- **THEN** its category is labelled "Electronics > Audio > Headphones"
