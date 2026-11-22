## ADDED Requirements

### Requirement: Favourite slugs list
A logged-in user SHALL be able to fetch, in one request, the slugs of all their favourite products as a flat list.

#### Scenario: Slugs returned
- **WHEN** a shopper who favourited "Aurora ANC Headphones" and "Nova 5G Phone" requests their favourite slugs
- **THEN** the response lists `aurora-anc-headphones` and `nova-5g-phone` and nothing else

#### Scenario: No favourites
- **WHEN** a shopper with no favourites requests their slugs
- **THEN** the response is an empty list

#### Scenario: Only own favourites
- **WHEN** another shopper's favourites exist
- **THEN** they do not appear in the list
