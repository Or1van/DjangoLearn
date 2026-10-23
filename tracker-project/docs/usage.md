# User guide

## First steps

1. **Sign up** at `/signup/` — you are logged in automatically and land on the dashboard.
   *(Or run `python manage.py seed_demo` and log in as `demo` / `demo12345` to explore with sample data.)*
2. **Create categories** under *Categories*: a name, an emoji and a colour (e.g. 🍕 Food, orange).
3. **Add a transaction** with *+ Expense* / *+ Income* on the dashboard or *+ Add* on the transactions page. Pick the type with the segmented switch, enter the amount, title, optional category and note. The date defaults to today.

## Pages

| Page | What you can do |
|---|---|
| **Dashboard** | See total balance, this month's income and expenses (with % change vs. last month), a 6-month chart, spending by category and recent transactions |
| **Transactions** | Search, filter by type / category / dates, use the quick pills (All time, This month, Last 30 days, This year), sort by date or amount, edit (✏️) or delete (🗑️) |
| **Categories** | Add, edit and delete categories; each card shows how much you spent in it |
| **Statistics** | All-time charts: expenses by category, income vs. expenses per month |

Filter dropdowns apply immediately; the three tiles on the transactions page always reflect the current filter.

## Interface settings

- **Language** – selector in the sidebar (English / Українська). Remembered in your browser.
- **Theme** – 🌙/☀️ button. Follows your OS setting until you choose manually.
- **Currency** – US dollars.

## Troubleshooting

| Problem | Fix |
|---|---|
| `You don't have permission to access that port` on Windows | Use another port: `python manage.py runserver 8080` |
| Charts are empty / missing | Chart.js is loaded from a CDN — check your internet connection |
| Ukrainian text not showing | Make sure `locale/uk/LC_MESSAGES/django.mo` exists; rebuild it as described in the README |
| Styles look outdated after an update | Hard-refresh the page (`Ctrl+F5`) |
| `no such column` / missing table errors | Run `python manage.py migrate` |

## Development

- Tests: see [testing.md](testing.md).
- Database: SQLite by default (`db.sqlite3`). Change `DATABASES` in `config/settings.py` for PostgreSQL etc.
- Before deploying: set a new `SECRET_KEY`, `DEBUG = False`, configure `ALLOWED_HOSTS`, run `collectstatic` and serve static files with a web server (or WhiteNoise).
