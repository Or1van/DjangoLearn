// Shared Chart.js helpers: theme-aware colours and money formatting.
window.Charts = (function () {
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const money = (v) => "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
  const registry = [];

  function applyTheme() {
    Chart.defaults.color = css("--muted");
    Chart.defaults.borderColor = css("--border");
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  }

  function make(canvas, config) {
    applyTheme();
    const chart = new Chart(canvas, config);
    registry.push({ chart, config });
    return chart;
  }

  document.addEventListener("themechange", () => {
    applyTheme();
    registry.forEach(({ chart }) => {
      if (chart.options.scales) {
        Object.values(chart.options.scales).forEach((s) => {
          s.grid = Object.assign(s.grid || {}, { color: css("--border") });
        });
      }
      if (chart.config.type === "doughnut") {
        chart.data.datasets.forEach((d) => (d.borderColor = css("--surface")));
      }
      chart.update();
    });
  });

  function doughnut(canvas, rows, legendEl) {
    const chart = make(canvas, {
      type: "doughnut",
      data: {
        labels: rows.map((r) => r.name),
        datasets: [{
          data: rows.map((r) => r.total),
          backgroundColor: rows.map((r) => r.color),
          borderColor: css("--surface"), borderWidth: 3, hoverOffset: 6,
        }],
      },
      options: {
        maintainAspectRatio: false, cutout: "68%",
        plugins: {
          legend: { display: !legendEl, position: "bottom" },
          tooltip: { callbacks: { label: (c) => ` ${c.label}: ${money(c.parsed)}` } },
        },
      },
    });
    if (legendEl) {
      const total = rows.reduce((a, r) => a + r.total, 0) || 1;
      rows.slice(0, 6).forEach((r) => {
        const row = document.createElement("div");
        row.className = "legend-row";
        const dot = document.createElement("span");
        dot.className = "dot"; dot.style.setProperty("--c", r.color);
        const name = document.createElement("span");
        name.textContent = (r.icon ? r.icon + " " : "") + r.name;
        const val = document.createElement("b");
        val.textContent = money(r.total) + " · " + Math.round((r.total / total) * 100) + "%";
        row.append(dot, name, val);
        legendEl.appendChild(row);
      });
    }
    return chart;
  }

  function incomeExpenseBars(canvas, months) {
    return make(canvas, {
      type: "bar",
      data: {
        labels: months.map((r) => r.month),
        datasets: [
          { label: window.I18N.income, data: months.map((r) => r.income),
            backgroundColor: "#10b981", borderRadius: 8, maxBarThickness: 28 },
          { label: window.I18N.expense, data: months.map((r) => r.expense),
            backgroundColor: "#f43f5e", borderRadius: 8, maxBarThickness: 28 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { beginAtZero: true, grid: { color: css("--border") }, ticks: { callback: money } },
          x: { grid: { display: false } },
        },
        plugins: {
          legend: { position: "bottom", labels: { usePointStyle: true } },
          tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${money(c.parsed.y)}` } },
        },
      },
    });
  }

  return { doughnut, incomeExpenseBars, money };
})();
