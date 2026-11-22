# Proposal

## Why

Sign-up accepts any password that is 8+ characters and not common or all digits, so `abcdefgh` is fine. We want a basic strength policy (a digit, an uppercase letter and a symbol). Reviewers also have to dig into the README for the demo logins, and the category-tree module has dead code and no worked examples explaining how it builds its lookups.

## What Changes

- Sign-up passwords must be at least 8 characters and contain at least 1 digit, 1 uppercase letter and 1 symbol, enforced through Django's password validation using the `django-password-validators` package (no hand-written validator).
- The three demo passwords change to ones that satisfy the policy; the hashes in `demo_users.json` are regenerated and the README table is updated.
- The login page shows a "Demo accounts" box (emails and passwords), only when `DEBUG` is on.
- `category_tree.py`: put worked examples (sample tree and the return value of each method) in the function docstrings, inline the single-use wrappers `build_category_tree` and `clear_category_tree_cache`, keep `get_category_tree()` as is, and drop unused members (`__contains__`, `CategoryNode.has_products`, and `CategoryNode.depth` with its one test usage).
- Add `vulture` as a dev dependency, run it over the project and remove whatever it confirms is unused.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `accounts`: sign-up passwords must meet the length, digit, uppercase and symbol rules.
- `demo-data`: demo passwords satisfy the sign-up rules, and the login page lists the demo accounts in development mode only.

The `category_tree.py` documentation and cleanup and the `vulture` pass change no behavior, so they have no spec delta.

## Impact

- Code: `config/settings.py` (validators, new app in `INSTALLED_APPS` if the package needs it), `config/urls.py` or `catalog/accounts.py` (pass the demo-accounts flag to the login view), `catalog/templates/registration/login.html`, `catalog/category_tree.py`, `catalog/signals.py`, `catalog/templatetags/catalog_extras.py`, whatever `vulture` confirms as dead.
- Data: `catalog/fixtures/demo_users.json` (new password hashes).
- Dependencies: `django-password-validators` (runtime), `vulture` (dev) in `pyproject.toml` and `uv.lock`.
- Tests: `test_accounts.py` (the shared valid password has no uppercase letter and must change), `test_demo_data.py` (demo passwords), `test_demo_data.py:26` (the `depth` use), new tests for each password rule and for the login box.
- Docs: README demo table, API example at README.md:209 and the sign-up validator sentence at README.md:135.
