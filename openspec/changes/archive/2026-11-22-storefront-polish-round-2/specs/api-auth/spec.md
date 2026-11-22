## MODIFIED Requirements

### Requirement: Obtain token pair
The API SHALL issue an access token and a refresh token in exchange for a valid email address and password at `/api/auth/token/`. The email SHALL be matched ignoring letter case. A `username` field SHALL NOT be required.

#### Scenario: Valid credentials
- **WHEN** a client posts the shopper's valid email and password to `/api/auth/token/`
- **THEN** it receives 200 with an access token and a refresh token

#### Scenario: Mixed-case email
- **WHEN** a client posts `Shopper@Example.com` for the account `shopper@example.com` with the correct password
- **THEN** it receives 200 with tokens

#### Scenario: Invalid credentials
- **WHEN** a client posts a wrong password
- **THEN** it receives 401 and no tokens
