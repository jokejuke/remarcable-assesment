## ADDED Requirements

### Requirement: Favourite slugs endpoint
`GET /api/favorites/slugs/` SHALL return a JSON array of the authenticated user's favourite product slugs, using a fixed number of queries regardless of how many favourites exist. Anonymous requests SHALL receive 401 or 403. It SHALL accept both token and session authentication.

#### Scenario: List of slugs
- **WHEN** a shopper with two favourites calls the endpoint
- **THEN** the response is 200 with a JSON array of two slugs

#### Scenario: Anonymous
- **WHEN** an anonymous client calls the endpoint
- **THEN** the response is 401 or 403 and no slugs are returned

#### Scenario: Query count
- **WHEN** the shopper has 1 or 20 favourites
- **THEN** the endpoint runs the same number of queries
