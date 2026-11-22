# Spec Delta

## ADDED Requirements

### Requirement: Password strength rules
A sign-up password SHALL be rejected unless it has at least 8 characters, at least 1 digit, at least 1 uppercase letter and at least 1 symbol (a printable character that is not a letter or digit). The form SHALL name each rule the password fails. These rules apply in addition to the existing common-password, all-digits and email-similarity checks.

#### Scenario: Valid strong password
- **WHEN** a visitor signs up with `Valid-pass-1` and a matching repeat
- **THEN** the account is created

#### Scenario: Too short
- **WHEN** a visitor signs up with `Ab1-xyz` (7 characters)
- **THEN** no account is created and the password field reports the minimum length of 8

#### Scenario: No digit
- **WHEN** a visitor signs up with `Valid-pass-x`
- **THEN** no account is created and the password field reports that a digit is required

#### Scenario: No uppercase letter
- **WHEN** a visitor signs up with `valid-pass-1`
- **THEN** no account is created and the password field reports that an uppercase letter is required

#### Scenario: No symbol
- **WHEN** a visitor signs up with `ValidPass123`
- **THEN** no account is created and the password field reports that a symbol is required

#### Scenario: Several rules fail at once
- **WHEN** a visitor signs up with `abcdefgh`
- **THEN** the password field reports the missing digit, uppercase letter and symbol together

### Requirement: Existing accounts keep logging in
Logging in SHALL NOT re-check the password rules, so accounts created before the rules existed continue to work.

#### Scenario: Old weak password
- **WHEN** an existing user whose password is `12345678` logs in with it
- **THEN** the login succeeds
