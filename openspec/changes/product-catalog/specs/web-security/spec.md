# Spec Delta

## Purpose

Protects the site and API against cross-site request forgery, uncontrolled cross-origin access and insecure configuration. Secrets and deployment settings are kept out of the code.

## ADDED Requirements

### Requirement: CSRF protection on state-changing forms
Every storefront, login and admin request that changes state SHALL require a valid CSRF token. Requests without one SHALL be rejected with 403.

#### Scenario: Buy without token
- **WHEN** a logged-in shopper's browser sends the Buy POST without a CSRF token
- **THEN** the response is 403 and no order is created

#### Scenario: Admin save without token
- **WHEN** a POST to an admin change form is sent without a CSRF token
- **THEN** the response is 403 and nothing changes

### Requirement: State changes only through POST-type methods
Endpoints that change state SHALL NOT accept GET requests.

#### Scenario: Favourite via GET
- **WHEN** a client sends GET to the storefront's add-favourite URL
- **THEN** the response is 405 and nothing changes

### Requirement: Cross-origin access is allowlisted
Cross-origin browser requests SHALL be allowed only from origins listed in an environment variable, and only for `/api/` paths. With no origins configured, no cross-origin access SHALL be allowed.

#### Scenario: Allowed origin
- **WHEN** `https://app.example.com` is configured and a browser on that origin calls GET `/api/products/`
- **THEN** the response carries CORS headers allowing that origin

#### Scenario: Unlisted origin
- **WHEN** a browser on an origin that is not listed calls the API
- **THEN** the response carries no CORS allow headers for that origin

#### Scenario: Non-API path
- **WHEN** an allowed origin requests a storefront page
- **THEN** no CORS headers are added

### Requirement: Cross-origin requests carry no cookies
CORS responses SHALL NOT allow credentials. Cross-origin clients SHALL authenticate with bearer tokens only.

#### Scenario: Credentialed request
- **WHEN** an allowed origin sends a request with cookies included
- **THEN** the response does not include `Access-Control-Allow-Credentials: true`

### Requirement: Cross-origin methods and headers are limited
CORS SHALL allow only GET, HEAD, OPTIONS, POST and DELETE, and SHALL allow the `Authorization` and `Content-Type` headers.

#### Scenario: PUT preflight
- **WHEN** an allowed origin sends a preflight for PUT
- **THEN** PUT is not listed in the allowed methods

### Requirement: Configuration from the environment
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the CORS allowlist, token lifetimes and the cache backend SHALL be read from environment variables. `DEBUG` SHALL default to off when unset.

#### Scenario: No DEBUG variable
- **WHEN** the application starts without a `DEBUG` variable
- **THEN** debug mode is off

#### Scenario: Missing secret in production
- **WHEN** the application starts with `DEBUG` off and no `SECRET_KEY`
- **THEN** startup fails with a clear configuration error

### Requirement: Production settings pass the deployment check
With production environment values set, Django's deployment check SHALL report no warnings. This includes secure and HTTP-only cookies, HSTS and clickjacking protection.

#### Scenario: Deployment check
- **WHEN** `manage.py check --deploy` runs with production environment values
- **THEN** it reports no issues

### Requirement: Clickjacking protection
Pages SHALL be served with a header that forbids embedding them in frames from other origins.

#### Scenario: Frame header
- **WHEN** any storefront page is requested
- **THEN** the response includes `X-Frame-Options: DENY`
