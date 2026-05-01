(function () {
  "use strict";

  const IS_AUTH_KEY = "ml_token";

  function isAuthenticated() {
    return Boolean(localStorage.getItem(IS_AUTH_KEY));
  }

  // Переключает .guest-only / .auth-only в зависимости от авторизации
  function applyAuthState() {
    const auth = isAuthenticated();
    document.querySelectorAll(".guest-only").forEach(el => {
      el.style.display = auth ? "none" : "";
    });
    document.querySelectorAll(".auth-only").forEach(el => {
      el.style.display = auth ? "" : "none";
    });
  }

  // Обновляем баланс в навбаре (только на страницах кабинета)
  function updateNavBalance() {
    const el = document.getElementById("nav-balance");
    if (!el || !isAuthenticated()) return;
    fetch("/balance/", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) el.textContent = data.amount.toFixed(2) + " кред."; })
      .catch(() => {});
  }

  // Flash-сообщения исчезают через 6 секунд
  function autoRemoveFlash() {
    document.querySelectorAll(".flash").forEach(el => {
      setTimeout(() => el.remove(), 6000);
    });
  }

  // Logout очищает флаг авторизации
  const logoutLink = document.querySelector('a[href="/logout"]');
  if (logoutLink) {
    logoutLink.addEventListener("click", () => {
      localStorage.removeItem(IS_AUTH_KEY);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    applyAuthState();
    autoRemoveFlash();
    if (document.querySelector(".dashboard-grid")) updateNavBalance();
  });
})();
