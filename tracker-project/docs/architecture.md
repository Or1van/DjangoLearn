# Architecture

## Overview

A classic server-rendered Django project. Pages are rendered by Django templates; JavaScript only enhances them (theme toggle, charts, small UX helpers). There is one JSON endpoint, used by the statistics page.

```
Browser ──HTTP──> config/urls.py ──> expenses/urls.py ──> expenses/views.py
                                                              │
                                   templates + static  <──────┤
                                   models / forms      <──────┘
                                   SQLite (db.sqlite3)
```

## Data model

**Category**

| Field | Type | Notes |
|---|---|---|
| user | FK(User) | cascade delete |
| name | CharField(50) | unique together with `user` |
| icon | CharField(8) | an emoji, default 🏷️ |
| color | CharField(7) | hex colour `#rrggbb` (validated), default `#6366f1` |

**Transaction**

| Field | Type | Notes |
|---|---|---|
| user | FK(User) | cascade delete |
| title | CharField(100) | |
| amount | Decimal(12,2) | must be ≥ 0.01 |
| kind | `expense` \| `income` | default `expense` |
| category | FK(Category), nullable | `SET_NULL` — deleting a category keeps its transactions |
| date | DateField | |
| note | TextField | optional |

Default ordering: newest date first (then newest id).

Amounts are always stored as positive numbers; `kind` decides the sign.

## Routes

| URL | Name | Description |
|---|---|---|
| `/` | `expenses:dashboard` | Overview: KPIs, charts, recent transactions |
| `/transactions/` | `expenses:list` | List with search, filters, sorting, pagination |
| `/add/` | `expenses:create` | New transaction (`?kind=income` preselects the type) |
| `/<id>/edit/` | `expenses:update` | Edit |
| `/<id>/delete/` | `expenses:delete` | Confirm (GET) and delete (POST) |
| `/categories/` | `expenses:category_list` | List and create categories |
| `/categories/<id>/edit/` | `expenses:category_update` | Edit name, icon, colour |
| `/categories/<id>/delete/` | `expenses:category_delete` | Confirm and delete |
| `/stats/` | `expenses:stats` | All-time statistics page |
| `/stats/data/` | `expenses:stats_api` | JSON used by `stats.js` |
| `/login/`, `/logout/`, `/signup/` | `login`, `logout`, `signup` | Authentication |
| `/i18n/setlang/` | `set_language` | Language switch (POST) |
| `/admin/` | | Django admin |

All `expenses:*` views require login; anonymous users are redirected to `/login/?next=…`. After login or sign-up the user lands on the dashboard.

## Security model

- Every query is filtered by `request.user`. Accessing another user's object returns **404**, not 403, so its existence is not leaked.
- Forms limit the `category` choices to the current user's categories, so a foreign category ID is rejected.
- Deletion needs a POST (with CSRF token) after a confirmation page. Logout and language switching are POST-only.
- Colours are validated against `^#[0-9a-fA-F]{6}$` because they are written into an inline `style` attribute.
- Sort/period/kind query parameters are checked against whitelists; invalid values are silently ignored (no 500s, no SQL built from user input).

## Dashboard (`/`)

Computed in `views.dashboard`:

- **Total balance** – all-time income minus expenses.
- **This month** – income, expenses, balance since the 1st of the current month.
- **Change vs. last month** – `(this − previous) / previous × 100` for expenses; hidden when there is no previous-month spending.
- **Top spend** – the category with the largest expense this month.
- **Trend** – income/expense for the last 6 calendar months (missing months are filled with zeros).
- **Chart data** is embedded in the page with `json_script` and read by `dashboard.js`, so the dashboard needs no extra request.

## Transaction list filters

`GET /transactions/` accepts:

| Parameter | Values | Effect |
|---|---|---|
| `q` | text | title / note contains (case-insensitive) |
| `kind` | `income` \| `expense` | |
| `category` | id | |
| `period` | `month` \| `30d` \| `year` | overrides `date_from` / `date_to` |
| `date_from`, `date_to` | `YYYY-MM-DD` | inclusive range |
| `sort` | `-date` (default), `date`, `-amount`, `amount` | |
| `page` | number | 15 items per page |

Totals (income, expense, balance) are computed on the filtered set across **all** pages, not just the visible one.

## Statistics API

`GET /stats/data/` returns:

```json
{
  "by_category": [{"name": "Food", "color": "#f59e0b", "total": 50.0}],
  "by_month":    [{"month": "2025-02", "income": 500.0, "expense": 37.0}]
}
```

`by_category` counts expenses only; uncategorised expenses appear as “Uncategorized” (translated).

## Internationalisation

`LocaleMiddleware` picks the language from the session/cookie set by Django's `set_language` view. Python code uses `gettext`, templates use `{% trans %}` / `{% blocktrans %}`, models use `gettext_lazy`. The Ukrainian catalog is `locale/uk/LC_MESSAGES/django.po`, compiled to `django.mo` (see the README for the command). Currency is fixed to USD (`$`).

## Frontend

See [frontend.md](frontend.md) for the CSS design system and JavaScript files.

## Management commands

`python manage.py seed_demo [--username U] [--password P]` creates a user with six categories and about six months of random but deterministic transactions (fixed random seed). It refuses to run if the username already exists.
