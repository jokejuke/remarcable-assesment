# Design

## Context

See proposal.md. Sign-up already calls Django's `validate_password()` ([accounts.py](../../../catalog/accounts.py)), driven by `AUTH_PASSWORD_VALIDATORS` in `config/settings.py`; no form code needs to change for the new rules. The login page is Django's stock `LoginView` wired in `config/urls.py`, and no `debug` context processor is enabled. Demo hashes live in `catalog/fixtures/demo_users.json`.

## Goals / Non-Goals

**Goals:**
- Password rules expressed as settings only, with no custom validator code.
- Demo credentials visible next to the login form in development, absent otherwise.
- `category_tree.py` readable on its own: each function's docstring shows a concrete example and its return value.

**Non-Goals:**
- Password reset, email verification or rate limiting.
- Re-validating existing passwords at login.
- A different public interface for the tree: `get_category_tree()` stays, and its callers do not change.

## Decisions

1. **`django-password-validators` over a hand-written regex validator.** Chosen by the user. Its character-class validator is configured in settings with a minimum count per class. Alternative: a `RegexValidator`, which needs no dependency but gives one generic error message. Exact option names (digits, uppercase, special characters) are confirmed from the installed package at implementation time. `MinimumLengthValidator` gets `min_length: 8` explicitly. The existing similarity, common-password and numeric validators stay.
2. **Symbol set.** The package's defaults also require letters and lower case and its special set has no `-`, so settings zero out the alpha and lower-case minimums and pass `string.punctuation` as the symbol set. The new demo passwords still include a `!` to make the rule obvious.
3. **Demo box gated in the view, not the template.** Pass the demo accounts to the login template through `extra_context` only when `settings.DEBUG` is true, so with `DEBUG` off the template receives nothing to render. Alternative: `django.template.context_processors.debug`, rejected because it also needs `INTERNAL_IPS`. The list of accounts is defined once and the README table repeats it; a test checks the two agree.
4. **New demo passwords** are `Demo-admin-123!`, `Demo-shopper-123!` and `Demo-shopper2-123!`. The fixture hashes are regenerated with `make_password` and edited into `demo_users.json`; users and favourites in that file stay as they are.
5. **Tree docstrings carry the examples.** One sample tree (Books; Electronics > Audio > Headphones, Electronics > Cameras) with its `children`, `visit` returns, `nodes` order, `path`, `descendant_ids` and `product_descendant_ids` results appears in the docstrings of the class and its methods, not in separate comments.
6. **Inline single-use wrappers only.** `build_category_tree` is folded into `get_category_tree` (one query, one constructor call) and `clear_category_tree_cache` becomes `transaction.on_commit(lambda: cache.delete(CACHE_KEY))` in `signals.py`. Anything used in several places stays a function.
7. **Dead code.** Remove `CategoryTree.__contains__` (no callers) and `CategoryNode.has_products` (the constructor reads the raw row, nothing outside reads the field). `CategoryNode.depth` goes too; the one test that uses it (`test_demo_data.py:26`) finds level-3 categories by counting " > " in the path instead. Then run `vulture` and delete only what is confirmed unused; its false positives (Django hooks such as `clean_*`, `get_*`, test methods) are not whitelisted into the codebase but skipped by hand.

## Risks / Trade-offs

- [The package's option names or default symbol set differ from what is assumed] → Read its documentation or source when adding it, and cover each rule with a test.
- [Credentials on the login page leak if `DEBUG` is on in a deployment] → The settings already require `SECRET_KEY` when `DEBUG` is off and the deploy check test covers a production env; a test asserts the box is absent with `DEBUG` off.
- [`vulture` flags framework-called code] → Review each hit before deleting; do not remove anything the framework calls by name.
- [New dependency] → Small, pure-Python, locked in `uv.lock`.
