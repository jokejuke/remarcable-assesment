## ADDED Requirements

### Requirement: Demo products have pictures
Every product in the catalog fixture SHALL have an absolute `http` or `https` picture URL. The fixture SHALL NOT embed image files.

#### Scenario: No product without a picture
- **WHEN** the catalog fixture is loaded
- **THEN** every product has a non-empty `image_url`

#### Scenario: Pictures are links only
- **WHEN** the repository is inspected
- **THEN** no product image files are stored in it
