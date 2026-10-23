# Expense Tracker

A multi-user personal finance tracker built with **Django**, plain **HTML/CSS** and vanilla **JavaScript**.

## Features

- Registration, login and logout (Django auth); each user only ever sees their own data
- Modern UI: sidebar layout, light/dark theme toggle, responsive (bottom tab bar on mobile), toast notifications, animated KPIs
- Dashboard: total balance, this month's income/expenses, change vs. last month, 6-month trend, spending by category, recent transactions
- Add / edit / delete income and expense transactions
- Personal categories with custom emoji icon and colour (unique per user)
- List with search, quick period pills (month / 30 days / year), filters (type, category, date range), sorting, pagination and live totals
- Statistics page with Chart.js charts (doughnut: expenses by category; bars: income vs. expenses by month) fed by a JSON endpoint
- Amounts in US dollars ($)
- English / Ukrainian interface, switchable from the navbar (Django i18n)
- Django admin for back-office access

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign up (on Windows use `runserver 8080` if port 8000 is blocked).

Want sample data? `python manage.py seed_demo` creates user `demo` / `demo12345` with six months of transactions.

## Running the tests

```bash
python manage.py test
```

107 tests cover models, forms, authentication, per-user data isolation, filtering, CRUD, categories, the statistics API, currency formatting and language switching.

```bash
python manage.py test                          # everything
python manage.py test expenses.tests.test_i18n # one module
python manage.py test -v 2                     # verbose
```

## Project layout

```
config/            Django project (settings, root URLs)
expenses/          Main app
  models.py        Category, Transaction
  forms.py         ModelForms scoped to the current user
  views.py         Function-based views + stats JSON API
  urls.py          App routes (namespace "expenses")
  templates/       App templates
  static/expenses/ style.css, app.js, charts.js, dashboard.js, stats.js
  management/      seed_demo command
  tests/           test_models, test_views, test_extra, test_i18n, test_dashboard
locale/uk/         Ukrainian translation (django.po / compiled django.mo)
templates/         base.html and registration/ (login, signup)
docs/              Detailed documentation
```

Documentation: [usage](docs/usage.md) · [architecture](docs/architecture.md) · [frontend & CSS](docs/frontend.md) · [testing](docs/testing.md).

## Translations

Edit `locale/uk/LC_MESSAGES/django.po`, then recompile the binary catalog:

```bash
python <python-install-dir>/Tools/i18n/msgfmt.py -o locale/uk/LC_MESSAGES/django.mo locale/uk/LC_MESSAGES/django.po
# or, with GNU gettext installed:
python manage.py compilemessages
```

The charts load Chart.js from the jsDelivr CDN, so the statistics page needs internet access.
