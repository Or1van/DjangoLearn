# Testing

The project uses Django's built-in `TestCase` (no extra packages). Each test runs in a transaction against a throw-away in-memory database, so your real `db.sqlite3` is never touched.

```bash
python manage.py test                                   # all 107 tests (~2 min, password hashing is slow by design)
python manage.py test expenses.tests.test_dashboard     # one module
python manage.py test expenses.tests.test_views.StatsTests.test_stats_api_empty   # one test
python manage.py test --parallel                        # use all CPU cores
python manage.py test -v 2                              # list every test as it runs
```

## What is covered

| Module | Covers |
|---|---|
| `test_models.py` | `__str__`, uniqueness of category names per user, amount validation, `SET_NULL` on category delete, ordering |
| `test_views.py` | Login requirement, sign-up, list totals, every filter, pagination, create / update / delete, per-user isolation, categories, statistics API |
| `test_extra.py` | Forms (stripping, user-scoped choices), combined filters, decimal precision, logout and login flows, edge cases |
| `test_i18n.py` | Language switching (en ↔ uk), translated labels and errors, dollar formatting |
| `test_dashboard.py` | Dashboard KPIs and chart data, month-over-month delta, period and sort filters, category icon/colour and editing, flash messages, the `seed_demo` command |

## Conventions

- Every view that touches user data has a test proving **another user cannot read or modify it** (expects 404).
- Tests that need a second user create `bob` next to `alice`.
- Dates in dashboard tests are relative to `timezone.localdate()` so they do not break when the calendar rolls over.

## Not covered

JavaScript (theme toggle, Chart.js rendering, count-up animation) is not unit-tested; test it by opening the app in a browser. Tests check that the HTML contains the right canvases and data, not how it looks.
