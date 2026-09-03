// Lógica dos formulários de login/registro (páginas auth).
(function () {
  function showError(msg) {
    const el = document.getElementById("error");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function clearError() {
    const el = document.getElementById("error");
    if (el) el.classList.add("hidden");
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearError();
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        window.location.href = "/";
      } else {
        showError(data.error || "Falha ao entrar.");
      }
    });
  }

  const regForm = document.getElementById("register-form");
  if (regForm) {
    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearError();
      const p1 = document.getElementById("password").value;
      const p2 = document.getElementById("password2").value;
      if (p1 !== p2) {
        showError("As senhas não coincidem.");
        return;
      }
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: p1,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        window.location.href = "/";
      } else {
        showError(data.error || "Falha ao criar conta.");
      }
    });
  }
})();
