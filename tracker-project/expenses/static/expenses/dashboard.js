// Dashboard charts: data is embedded by the server via json_script.
(function () {
  const data = JSON.parse(document.getElementById("dash-data").textContent);
  Charts.incomeExpenseBars(document.getElementById("trend"), data.trend);
  const cats = document.getElementById("cats");
  if (cats) Charts.doughnut(cats, data.by_category, document.getElementById("legend"));
})();
