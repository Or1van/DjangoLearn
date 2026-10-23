// Fetches aggregated data from the JSON API and renders Chart.js charts.
(async function () {
  const resp = await fetch(window.STATS_URL, { credentials: "same-origin" });
  const data = await resp.json();

  if (!data.by_category.length && !data.by_month.length) {
    document.getElementById("stats-empty").hidden = false;
    document.querySelectorAll(".chart-box").forEach((el) => (el.closest(".card").hidden = true));
    return;
  }
  Charts.doughnut(document.getElementById("by-category"), data.by_category);
  Charts.incomeExpenseBars(document.getElementById("by-month"), data.by_month);
})();
