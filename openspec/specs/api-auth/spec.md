# api-auth Specification

## Purpose

Authenticates users of the storefront and the API. Browser pages use a session, and API clients use short-lived JSON Web Tokens with refresh rotation and server-side revocation on logout.

## Requirements

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

### Requirement: Bearer access tokens
API requests SHALL be authenticated by an `Authorization: Bearer <access token>` header. Expired or invalid tokens SHALL be rejected with 401.

#### Scenario: Valid token
- **WHEN** a client calls GET `/api/favorites/` with a valid access token
- **THEN** the request is authenticated as the token's user

#### Scenario: Expired token
- **WHEN** a client uses an access token past its lifetime
- **THEN** it receives 401

### Requirement: Token lifetimes are configurable
Access tokens SHALL expire after 15 minutes and refresh tokens after 1 day by default. Both lifetimes SHALL be configurable through environment variables.

#### Scenario: Default lifetime
- **WHEN** no lifetime variables are set
- **THEN** a newly issued access token expires 15 minutes after issue

### Requirement: Refresh rotates tokens
Refreshing at `/api/auth/token/refresh/` SHALL return a new access token and a new refresh token, and the used refresh token SHALL no longer be accepted.

#### Scenario: Reusing a refresh token
- **WHEN** a client refreshes with a refresh token and then tries the same refresh token again
- **THEN** the second attempt is rejected with 401

### Requirement: Logout revokes the refresh token
Posting a refresh token to `/api/auth/logout/` SHALL revoke it so it cannot be used again. Access tokens already issued remain valid until they expire.

#### Scenario: Refresh after logout
- **WHEN** a client logs out with its refresh token and then tries to refresh with it
- **THEN** the refresh is rejected with 401

### Requirement: Session authentication for browser pages
Storefront pages and same-site browser requests to the API SHALL authenticate through the login session. Session-authenticated API writes SHALL require a valid CSRF token.

#### Scenario: Swagger with session
- **WHEN** a user logged in through the site calls GET `/api/orders/` from Swagger UI
- **THEN** the request is authenticated by the session

#### Scenario: Session write without CSRF token
- **WHEN** a session-authenticated client sends POST `/api/favorites/` without a CSRF token
- **THEN** it receives 403 and nothing changes

### Requirement: Tokens are never persisted in fixtures or pages
No token SHALL be committed to the repository or rendered into storefront pages. Storefront pages SHALL rely only on the session.

#### Scenario: Storefront page source
- **WHEN** a logged-in user views the storefront page source
- **THEN** it contains no access or refresh token
