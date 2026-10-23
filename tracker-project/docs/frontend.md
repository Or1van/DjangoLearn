# Frontend

No build step, no bundler, no npm. Everything is plain HTML, CSS and JavaScript served by Django's static files.

## Files

| File | Purpose |
|---|---|
| `expenses/static/expenses/style.css` | The whole design system |
| `expenses/static/expenses/app.js` | Theme toggle, toasts, filter auto-submit, default date, KPI count-up |
| `expenses/static/expenses/charts.js` | Shared Chart.js helpers (doughnut, income/expense bars, theme-aware colours) |
| `expenses/static/expenses/dashboard.js` | Dashboard charts, reads data from `<script id="dash-data">` |
| `expenses/static/expenses/stats.js` | Statistics page: fetches `/stats/data/` and draws the charts |
| `templates/base.html` | Layout: sidebar (or guest card), toasts, script loading |

Chart.js 4.4.1 is loaded from the jsDelivr CDN only on pages that show charts.

## About the CSS

`style.css` is plain, readable text — nothing is encrypted, obfuscated or minified. It is formatted one declaration per line, with a comment header for each section (design tokens, app shell, cards/buttons/forms, KPI, layout, table, filters, categories, toasts, responsive). You can open it in any editor, and browsers show it unmodified in DevTools (F12 → Elements → Styles).

## Design tokens

All colours, radii and shadows are CSS custom properties declared at the top of `style.css`:

```css
:root            { --bg:#f5f6fb; --surface:#fff; --primary:#6366f1; --income:#10b981; … }
[data-theme="dark"] { --bg:#0b0d17; --surface:#141829; --primary:#818cf8; … }
```

Components use `var(--primary)` etc. instead of hard-coded colours, so:

- **Re-theming** = changing a handful of values at the top of the file.
- **Dark mode** = the same variables redefined under `[data-theme="dark"]`.

## Theme switching

1. A tiny inline script in `<head>` reads `localStorage.theme` (or the OS preference `prefers-color-scheme`) and sets `<html data-theme="…">` *before* first paint, so there is no flash of the wrong theme.
2. `app.js` toggles the attribute on click, saves it and dispatches a `themechange` event.
3. `charts.js` listens for that event and recolours existing charts (grid lines, borders).

## Layout and responsiveness

- Desktop: CSS grid, 248 px sidebar + content (`.app`).
- ≤ 900 px: the sidebar becomes a fixed bottom tab bar; language/theme/logout controls move to the top-right corner; two-column grids collapse to one.
- ≤ 560 px: less important table columns (`.hide-sm`) are hidden.
- `prefers-reduced-motion` disables animations.

## Components cheat sheet

| Class | Use |
|---|---|
| `.card` | White rounded panel with shadow |
| `.kpi` (+ `.income`, `.expense`, `.balance`, `.hero`) | Statistic tiles |
| `.btn` (+ `.secondary`, `.danger`, `.income`, `.sm`, `.block`) | Buttons |
| `.cat-chip` | Coloured category pill; set `style="--c:#hex"` |
| `.seg` | Segmented radio control (Expense / Income) |
| `.pill` / `.pills` | Quick period filters |
| `.toast` | Notification from Django `messages` |
| `.empty` | Empty-state placeholder |

Category colours are passed to CSS through the `--c` variable and blended with `color-mix()`, so chips and icons get a tinted background that works in both themes.

## Adding a chart

1. Add a `<canvas id="…">` in a template.
2. Provide data (via `json_script` or `fetch`).
3. Call `Charts.doughnut(canvas, rows, legendEl?)` or `Charts.incomeExpenseBars(canvas, months)` from a small page script.
