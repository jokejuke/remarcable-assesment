# deployment Specification

## Purpose

Defines how the application is packaged and run in containers: one command that runs the project's checks the way CI would, and a production stack with a TLS front end, an application server, static files and persistent data.

## Requirements

### Requirement: Containerised check suite
The project SHALL provide a container image target that runs the unit tests, the migration check, the OpenAPI schema validation and the lint check, and exits non-zero if any of them fails. It SHALL need no environment variables from the caller.

#### Scenario: Checks pass
- **WHEN** the test target is run on a clean checkout
- **THEN** all four checks run and the container exits with status 0

#### Scenario: A test fails
- **WHEN** a unit test fails
- **THEN** the container exits with a non-zero status

#### Scenario: No caller environment
- **WHEN** the test target is run without `.env` or any `-e` options
- **THEN** it still starts and runs the checks

### Requirement: Production stack serves the site over HTTPS
The production stack SHALL publish only the nginx service. nginx SHALL redirect HTTP requests to HTTPS and serve the storefront, admin and API over HTTPS using certificates supplied from outside the image.

#### Scenario: HTTP request
- **WHEN** a client requests any path over HTTP
- **THEN** it receives a redirect to the same path over HTTPS

#### Scenario: HTTPS request
- **WHEN** a client requests `/` over HTTPS
- **THEN** the storefront is returned with status 200

#### Scenario: Application server not exposed
- **WHEN** the stack is running
- **THEN** the application server's port is not reachable from the host

#### Scenario: Secure cookies behind the proxy
- **WHEN** a user logs in over HTTPS
- **THEN** the session cookie is set with the Secure flag and no redirect loop occurs

### Requirement: Client-supplied forwarding headers are not trusted
nginx SHALL set the forwarded protocol header itself from the connection it received, discarding any value sent by the client.

#### Scenario: Spoofed header
- **WHEN** a client sends `X-Forwarded-Proto: https` over plain HTTP
- **THEN** the request is still redirected to HTTPS and the header value is not passed to the application

### Requirement: Static files in production
nginx SHALL serve `/static/` from files collected when the images are built. The admin and API documentation pages SHALL load their styles and scripts with `DEBUG` off.

#### Scenario: Admin styles
- **WHEN** a browser opens `/admin/login/` over HTTPS
- **THEN** its stylesheet at `/static/admin/css/base.css` is returned with status 200

### Requirement: Production configuration is explicit
The production stack SHALL refuse to start without `SECRET_KEY` and `ALLOWED_HOSTS`, and SHALL run with `DEBUG` off. The repository SHALL contain no real secret or certificate.

#### Scenario: Missing secret key
- **WHEN** the stack is started with no `SECRET_KEY`
- **THEN** startup fails with a message naming the variable

#### Scenario: Debug off
- **WHEN** the stack is running
- **THEN** an unknown URL returns a plain 404 page without debug details

### Requirement: Data persists across restarts
The production stack SHALL keep the SQLite database on a named volume. Migrations SHALL be applied automatically when the application container starts and SHALL be safe to repeat.

#### Scenario: Restart
- **WHEN** the stack is stopped and started again
- **THEN** previously created accounts and orders are still present

#### Scenario: Fresh volume
- **WHEN** the stack starts with an empty data volume
- **THEN** the schema is created before the server accepts requests

### Requirement: No demo data in production
The production containers SHALL NOT load the demo fixtures or create the demo accounts.

#### Scenario: Fresh production start
- **WHEN** the stack starts on an empty volume
- **THEN** no user with a demo account email exists

### Requirement: Unprivileged runtime
The application container SHALL run as a non-root user, and images SHALL NOT contain `.env` files, database files or `.git`.

#### Scenario: Process user
- **WHEN** the application container is running
- **THEN** its server process does not run as root

#### Scenario: Image contents
- **WHEN** the application image's file system is inspected
- **THEN** it contains no `.env`, `*.sqlite3` or `.git` entries

### Requirement: Single application process
The application server SHALL run as one worker process with multiple threads, consistent with the per-process category cache and SQLite's single writer.

#### Scenario: Category edit
- **WHEN** an administrator edits a category
- **THEN** the next storefront request shows the updated tree
