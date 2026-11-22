#!/bin/sh
# Runs every check even if one fails, then exits non-zero if any did.
status=0
run() { echo "==> $*"; "$@" || status=1; }

run python manage.py test
run python manage.py makemigrations --check
run python manage.py spectacular --validate --fail-on-warn --file /dev/null
run ruff check

exit $status
