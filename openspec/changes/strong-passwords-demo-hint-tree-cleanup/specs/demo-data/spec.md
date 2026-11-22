# Spec Delta

## ADDED Requirements

### Requirement: Demo passwords follow the sign-up rules
Every demo account password SHALL satisfy the sign-up password strength rules, so the demo data does not contradict the site's own policy.

#### Scenario: Demo passwords pass validation
- **WHEN** each documented demo password is checked against the site's password rules
- **THEN** none is rejected

#### Scenario: Documented credentials log in
- **WHEN** a demo account logs in with the password listed in the README
- **THEN** the login succeeds

### Requirement: Demo accounts shown on the login page in development
When `DEBUG` is on, the login page SHALL show a "Demo accounts" box listing each demo account's email and password. When `DEBUG` is off, the page SHALL NOT contain any demo email or password.

#### Scenario: Development login page
- **WHEN** `DEBUG` is on and an anonymous visitor opens the login page
- **THEN** the page lists `admin@example.com`, `shopper@example.com` and `shopper2@example.com` with their passwords

#### Scenario: Production login page
- **WHEN** `DEBUG` is off and an anonymous visitor opens the login page
- **THEN** the page contains no demo email or password
