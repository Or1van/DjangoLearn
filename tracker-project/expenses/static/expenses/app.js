// UX helpers: theme toggle, toasts, filters auto-submit, default date, number count-up.
document.addEventListener("DOMContentLoaded", () => {
  // Theme toggle (persisted in localStorage)
  const root = document.documentElement;
  const toggle = document.getElementById("theme-toggle");
  const paint = () => { if (toggle) toggle.textContent = root.dataset.theme === "dark" ? "☀️" : "🌙"; };
  paint();
  if (toggle) {
    toggle.addEventListener("click", () => {
      root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
      try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
      paint();
      document.dispatchEvent(new Event("themechange"));
    });
  }

  // Toasts auto-dismiss
  document.querySelectorAll(".toast").forEach((el, i) => {
    setTimeout(() => el.classList.add("hide"), 3500 + i * 400);
    setTimeout(() => el.remove(), 4100 + i * 400);
    el.addEventListener("click", () => el.remove());
  });

  // Default today's date on the add form
  const dateInput = document.querySelector("#tx-form input[name=date]");
  if (dateInput && !dateInput.value) {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    dateInput.value = d.toISOString().slice(0, 10);
  }

  // Auto-submit filters when a select/date changes
  const filters = document.getElementById("filters");
  if (filters) {
    filters.querySelectorAll("select, input[type=date]").forEach((el) =>
      el.addEventListener("change", () => filters.submit())
    );
  }

  // Count-up animation for KPI values
  document.querySelectorAll("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count);
    if (Number.isNaN(target) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const final = el.textContent;
    const t0 = performance.now(), dur = 700;
    const fmt = (v) => (v < 0 ? "-" : "") + "$" +
      Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const tick = (now) => {
      const p = Math.min((now - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = p < 1 ? fmt(target * e) : final;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
});
