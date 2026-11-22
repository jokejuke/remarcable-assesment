## ADDED Requirements

### Requirement: Email shown as identity
Wherever the site shows who is signed in, it SHALL show the account's email address, and every sign-in or sign-up form on the site SHALL ask for "Email", not "Username".

#### Scenario: Header identity
- **WHEN** `shopper@example.com` is logged in
- **THEN** the header shows "Signed in as shopper@example.com"
