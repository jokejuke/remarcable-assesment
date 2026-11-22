# Tasks

## 1. Password rules

- [x] 1.1 Add `django-password-validators` with `uv add`, register it if the package requires an app entry, and verify `uv run python manage.py check` passes
- [x] 1.2 Configure its character-class validator (1 digit, 1 uppercase, 1 symbol) and set `MinimumLengthValidator` to `min_length: 8` in `AUTH_PASSWORD_VALIDATORS`, and verify with a shell call to `validate_password("abcdefgh")` that all three missing classes are reported
- [x] 1.3 In `test_accounts.py`, change the shared valid `PASSWORD` so it passes the new rules, add tests for each scenario in the accounts delta (too short, no digit, no uppercase, no symbol, several at once, strong password accepted, old weak password still logs in), and verify `uv run pytest catalog/tests/test_accounts.py` passes
- [x] 1.4 Update the validator sentence at README.md:135 and verify it lists the new rules

## 2. Demo accounts

- [x] 2.1 Regenerate the three hashes in `catalog/fixtures/demo_users.json` for the new passwords, leaving users and favourites unchanged, and verify by loading the fixtures into a scratch database and logging in with each password
- [x] 2.2 Pass the demo accounts to the login template through `extra_context` only when `DEBUG` is on, and add the "Demo accounts" box to `login.html`
- [x] 2.3 Update the README demo table and the API example at README.md:209, and update the passwords in `test_demo_data.py`
- [x] 2.4 Add tests: the box lists all three accounts with `DEBUG` on, the page contains no demo email or password with `DEBUG` off, the documented passwords pass `validate_password`, and verify `uv run pytest catalog/tests/test_demo_data.py` passes

## 3. Category tree docs and dead code

- [x] 3.1 Rewrite the docstrings in `category_tree.py` with the worked example and the return value of each method, and verify by running the example in a shell that the documented values are what the code returns
- [x] 3.2 Fold `build_category_tree` into `get_category_tree` and inline `clear_category_tree_cache` in `signals.py`, keeping `get_category_tree()` for all other callers, and verify `uv run pytest catalog/tests/test_category_hierarchy.py` passes
- [x] 3.3 Remove `CategoryTree.__contains__`, `CategoryNode.has_products` and `CategoryNode.depth`, rewrite the level-3 lookup in `test_demo_data.py:26`, and verify the tests and `ruff check .` pass

## 4. Dead code sweep

- [x] 4.1 Add `vulture` as a dev dependency, run it over `catalog` and `config`, and review each finding by hand
- [x] 4.2 Delete only the confirmed-unused code and verify the full suite `uv run pytest` and `ruff check .` pass
