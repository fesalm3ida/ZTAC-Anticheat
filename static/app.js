// Lógica do dashboard do anti-cheat.
(function () {
  const $ = (id) => document.getElementById(id);

  const SEVERITY_STYLE = {
    ok:       { text: "text-emerald-400", bg: "bg-emerald-950/50",  border: "border-emerald-900" },
    low:      { text: "text-cyan-300",     bg: "bg-cyan-950/40",     border: "border-cyan-900" },
    medium:   { text: "text-amber-300",    bg: "bg-amber-950/40",    border: "border-amber-900" },
    high:     { text: "text-orange-300",   bg: "bg-orange-950/40",   border: "border-orange-900" },
    critical: { text: "text-rose-300",     bg: "bg-rose-950/50",     border: "border-rose-900" },
  };

  const VERDICT = {
    limpo: { label: "LIMPO",       cls: "bg-emerald-950/60 border-emerald-700 text-emerald-300", bar: "bg-emerald-500" },
    suspeito: { label: "SUSPEITO", cls: "bg-amber-950/60 border-amber-700 text-amber-300", bar: "bg-amber-500" },
    hackeado: { label: "HACKEADO", cls: "bg-rose-950/60 border-rose-700 text-rose-300", bar: "bg-rose-500" },
    indisponivel: { label: "INDISPONÍVEL", cls: "bg-slate-800/60 border-slate-700 text-slate-300", bar: "bg-slate-500" },
    sem_processo: { label: "SEM PROCESSO", cls: "bg-amber-950/60 border-amber-700 text-amber-300", bar: "bg-amber-500" },
  };

  const STAGE_NOTE = { A: "Módulos", B: "Detours / Integridade", C: "Artefatos & Strings" };

  // ------------------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function severityStyle(sev) { return SEVERITY_STYLE[sev] || SEVERITY_STYLE.low; }

  // ------------------------------------------------------------------
  async function api(path, opts) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  // ------------------------------------------------------------------
  // Estado inicial da área de resultado (antes/limpo de uma varredura)
  // ------------------------------------------------------------------
  function resetDisplay() {
    $("verdict-empty").classList.remove("hidden");
    $("verdict-empty").textContent = "Nenhuma varredura executada.";
    $("verdict").classList.add("hidden");
    $("results").innerHTML =
      '<p class="text-sm text-slate-400">Inicie uma varredura para ver os achados.</p>';
    $("report-time").textContent = "";
  }

  // ------------------------------------------------------------------
  // Render do relatório (veredito + achados)
  // ------------------------------------------------------------------
  function renderReport(report) {
    const v = VERDICT[report.verdict] || VERDICT.indisponivel;

    $("verdict-empty").classList.add("hidden");
    $("verdict").classList.remove("hidden");

    const banner = $("verdict-banner");
    banner.className = "rounded-xl px-5 py-4 border " + v.cls;
    banner.innerHTML =
      '<span class="text-2xl font-bold tracking-widest">' + v.label + "</span>" +
      '<span class="block text-sm mt-1 opacity-90">' +
      (report.simulated ? "Varredura simulada (demo)" : "Varredura em processo real") +
      "</span>";

    $("score-num").textContent = report.score;
    $("score-bar").className = "h-full rounded-full transition-all duration-500 " + v.bar;
    $("score-bar").style.width = report.score + "%";

    $("stat-findings").textContent = report.findings.length;
    $("stat-modules").textContent = report.modules_checked;

    // agrupa por estágio
    const groups = {};
    report.findings.forEach((f) => {
      (groups[f.stage] = groups[f.stage] || []).push(f);
    });

    const results = $("results");
    results.innerHTML = "";
    const stages = Object.keys(groups).sort();
    stages.forEach((stage) => {
      const card = document.createElement("div");
      card.className = "mb-4 border border-slate-800 rounded-xl overflow-hidden";
      const head = document.createElement("div");
      head.className = "px-4 py-2.5 bg-slate-800/40 flex items-center justify-between";
      head.innerHTML =
        '<span class="text-xs font-semibold uppercase tracking-wide text-slate-300">' +
        "Estágio " + stage + " — " + (STAGE_NOTE[stage] || "Geral") + "</span>";
      card.appendChild(head);

      const list = document.createElement("div");
      list.className = "divide-y divide-slate-800";
      groups[stage].forEach((f) => {
        const st = severityStyle(f.severity);
        const row = document.createElement("div");
        row.className = "px-4 py-3 flex gap-3";
        row.innerHTML =
          '<span class="mt-1 w-2 h-2 rounded-full shrink-0" style="background:' +
          (f.severity === "critical" ? "#f43f5e" : f.severity === "high" ? "#fb923c" :
             f.severity === "medium" ? "#fcd34d" : f.severity === "low" ? "#67e8f9" : "#34d399") +
          '"></span>' +
          '<div class="min-w-0">' +
            '<div class="flex items-center gap-2 flex-wrap">' +
              '<span class="font-medium text-slate-100 text-sm">' + esc(f.title) + "</span>" +
              '<span class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full border ' +
              st.bg + " " + st.border + " " + st.text + '">' + esc(f.severity) + "</span>" +
            "</div>" +
            '<p class="text-xs text-slate-400 mt-0.5">' + esc(f.detail) + "</p>" +
            (f.evidence && f.evidence.length
              ? '<div class="mt-1.5 flex flex-wrap gap-1.5">' +
                f.evidence.filter(Boolean).map((e) =>
                  '<code class="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded">' + esc(e) + "</code>"
                ).join("") + "</div>"
              : "") +
          "</div>";
        list.appendChild(row);
      });
      card.appendChild(list);
      results.appendChild(card);
    });

    $("report-time").textContent = report.timestamp || "";
  }

  // ------------------------------------------------------------------
  // Aviso: processo do Counter-Strike não encontrado
  // ------------------------------------------------------------------
  function renderProcessNotFound(report) {
    $("verdict-empty").classList.remove("hidden");
    $("verdict-empty").textContent = "Nenhuma varredura executada.";
    $("verdict").classList.add("hidden");

    const results = $("results");
    results.innerHTML = "";
    const w = document.createElement("div");
    w.className = "rounded-xl border border-amber-900 bg-amber-950/40 p-5";
    w.innerHTML =
      '<div class="flex items-start gap-3">' +
        '<svg class="w-6 h-6 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">' +
          '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86l-7.5 13A2 2 0 0 0 4.5 20h15a2 2 0 0 0 1.71-3.14l-7.5-13a2 2 0 0 0-3.42 0z"/>' +
        "</svg>" +
        "<div>" +
          '<p class="font-semibold text-amber-300">Processo do Counter-Strike não encontrado</p>' +
          '<p class="text-sm text-amber-200/90 mt-1">' +
            esc(report.warning || "Nenhum processo do jogo em execução.") +
          "</p>" +
        "</div>" +
      "</div>";
    results.appendChild(w);

    $("report-time").textContent = report.timestamp || "";
    $("scan-status").textContent = "Aviso: nenhum processo do CS em execução.";
  }

  // ------------------------------------------------------------------
  async function runScan(payload) {
    $("scan-status").textContent = "Varrendo…";
    const { ok, data } = await api("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!ok) {
      $("scan-status").textContent = data.error || "Falha na varredura.";
      return;
    }
    if (data.verdict === "sem_processo") {
      renderProcessNotFound(data);
    } else {
      renderReport(data);
      $("scan-status").textContent = "Concluído em " + (data.timestamp || "");
    }
    loadHistory();
  }

  // ------------------------------------------------------------------
  async function loadHistory() {
    const { ok, data } = await api("/api/reports");
    if (!ok) return;
    const wrap = $("history");
    const rows = data.reports || [];
    if (!rows.length) {
      wrap.textContent = "Sem registros.";
      return;
    }
    wrap.innerHTML = "";
    rows.forEach((r) => {
      const item = document.createElement("div");
      item.className = "flex items-center justify-between py-2 border-b border-slate-800 last:border-0 cursor-pointer hover:bg-slate-800/30 px-2 rounded";
      const v = VERDICT[r.verdict] || VERDICT.indisponivel;
      item.innerHTML =
        '<div class="flex items-center gap-3">' +
          '<span class="text-xs font-semibold ' + v.cls.split(" ")[2] + '">' + v.label + "</span>" +
          '<span class="text-slate-300 text-xs">' + esc(r.process_name || "") + " · pid " + esc(r.process_pid || "") + "</span>" +
        "</div>" +
        '<span class="text-xs text-slate-500">' + esc(r.created_at || "") + "</span>";
      item.addEventListener("click", () => loadReport(r.id));
      wrap.appendChild(item);
    });
  }

  async function loadReport(id) {
    const { ok, data } = await api("/api/reports/" + id);
    if (!ok || !data.report) return;
    if (data.report.verdict === "sem_processo") renderProcessNotFound(data.report);
    else renderReport(data.report);
  }

  // ------------------------------------------------------------------
  async function init() {
    const me = await api("/api/me");
    if (!me.data.authenticated) {
      window.location.href = "/login";
      return;
    }
    $("user-name").textContent = me.data.user.username;

    const procs = await api("/api/processes");
    if (procs.ok) {
      const sel = $("process");
      sel.innerHTML = '<option value="">Auto-detectar (nenhum)</option>';
      const badge = $("mode-badge");
      const isDemo = procs.data.mode === "demo";
      badge.textContent = isDemo ? "MODO DEMO" : "SCAN REAL";
      badge.className = "px-2 py-0.5 rounded-full border text-xs " +
        (isDemo ? "bg-amber-950/40 border-amber-800 text-amber-300"
                : "bg-emerald-950/40 border-emerald-800 text-emerald-300");

      // Controles exclusivos do modo demo
      if (isDemo) {
        $("no-proc-wrap").classList.remove("hidden");
      } else {
        $("clean-btn").classList.add("hidden");
        $("no-proc-wrap").classList.add("hidden");
      }

      // Preenche a lista de processos detectados
      (procs.data.processes || []).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.pid;
        opt.textContent = p.name + " (pid " + p.pid + ")";
        sel.appendChild(opt);
      });
    }

    $("scan-btn").addEventListener("click", () => {
      const val = $("process").value;
      const noProc = $("no-process").checked;
      runScan({ pid: val ? parseInt(val, 10) : null, no_process: noProc });
    });

    $("clean-btn").addEventListener("click", () => {
      // "simular processo limpo" ignora o processo atual; desmarca o toggle
      $("no-process").checked = false;
      runScan({ pid: null, clean: true });
    });

    $("clear-process").addEventListener("click", () => {
      // Limpa a seleção e a lista de processos (nenhum fica no dropdown);
      // o histórico é mantido.
      const sel = $("process");
      sel.innerHTML = '<option value="">Auto-detectar (nenhum)</option>';
      sel.value = "";
      $("no-process").checked = false;
      resetDisplay();
      $("scan-status").textContent =
        "Processo limpo — nenhum processo na seleção; o histórico foi mantido.";
    });

    $("logout").addEventListener("click", async () => {
      await api("/api/logout", { method: "POST" });
      window.location.href = "/login";
    });

    loadHistory();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
