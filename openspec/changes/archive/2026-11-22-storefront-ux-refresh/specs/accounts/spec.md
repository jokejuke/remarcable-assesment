# Spec Delta

## Purpose

Lets visitors create their own shopper account with an email address and log in with it, so they can buy products and keep favourites.

## ADDED Requirements

### Requirement: Visitor sign-up
The storefront SHALL provide a sign-up page where an anonymous visitor creates an account with an email address and a password entered twice. The new account SHALL have no admin access. After sign-up the visitor SHALL be logged in.

#### Scenario: Successful sign-up
- **WHEN** a visitor signs up with `new@example.com` and a valid password entered twice
- **THEN** an account is created, the visitor is logged in and the header shows `new@example.com`

#### Scenario: New account has no admin access
- **WHEN** a newly signed-up user opens `/admin/`
- **THEN** access is denied

#### Scenario: Logged-in user opens sign-up
- **WHEN** a logged-in user opens the sign-up page
- **THEN** they are redirected to the home page

### Requirement: Email address is the username
The email address entered at sign-up SHALL become the account's username and email, stored in lower case. Each email address SHALL belong to at most one account, ignoring letter case.

#### Scenario: Username stored as email
- **WHEN** a visitor signs up with `Ann@Example.com`
- **THEN** the account's username and email are both `ann@example.com`

#### Scenario: Duplicate email
- **WHEN** a visitor signs up with `SHOPPER@example.com` while `shopper@example.com` exists
- **THEN** no account is created and the form shows that the email is already registered

### Requirement: Sign-up input is validated
The sign-up form SHALL reject an invalid email address, passwords that do not match, and passwords that fail the site's password rules, showing the errors and creating no account.

#### Scenario: Invalid email
- **WHEN** a visitor signs up with `not-an-email`
- **THEN** no account is created and the email field shows an error

#### Scenario: Passwords differ
- **WHEN** the two password entries do not match
- **THEN** no account is created and the form shows an error

#### Scenario: Weak password
- **WHEN** a visitor signs up with the password `12345678`
- **THEN** no account is created and the form shows the password rule that failed

### Requirement: Login by email address
The login form SHALL label its first field "Email" and SHALL accept the account's email address in any letter case.

#### Scenario: Mixed-case email
- **WHEN** `shopper@example.com` logs in as `Shopper@Example.com` with the correct password
- **THEN** the login succeeds

#### Scenario: Wrong password
- **WHEN** a user logs in with a correct email and a wrong password
- **THEN** the login fails with a message that does not say which of the two was wrong

### Requirement: Sign-up and login keep the return target
The login page SHALL link to the sign-up page and the sign-up page SHALL link to the login page, both carrying the same `next` target. After a successful sign-up or login the user SHALL be sent to that target if it is on this site, otherwise to the home page.

#### Scenario: Sign-up from a Buy redirect
- **WHEN** an anonymous visitor clicks Buy on a product page, follows the sign-up link from the login page and signs up
- **THEN** they are logged in and returned to that product page, and no order is placed

#### Scenario: External target
- **WHEN** the sign-up form is submitted with `next=https://evil.example`
- **THEN** the new user is sent to the home page
