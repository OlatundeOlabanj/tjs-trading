/* ── CLOCK ─────────────────────────────────────────────── */
function updateClock() {
  const el = document.getElementById("topClock");
  if (!el) return;
  el.textContent = new Date().toUTCString().split(" ")[4] + " UTC";
}
setInterval(updateClock, 1000);
updateClock();

/* ── STATUS ─────────────────────────────────────────────── */
function setStatus(type, text) {
  const bar  = document.getElementById("statusBar");
  const icon = document.getElementById("statusIcon");
  const txt  = document.getElementById("statusText");
  if (!bar) return;
  bar.className = "status-bar " + (type || "");
  txt.textContent = text;
  const icons = {
    scanning: `<div class="spinner"></div>`,
    done: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    error: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--red)" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    "": `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
  };
  if (icon) icon.innerHTML = icons[type] || icons[""];
}

/* ── LOG ─────────────────────────────────────────────────── */
function log(msg, type = "") {
  const el = document.getElementById("progressLog");
  if (!el) return;
  el.style.display = "block";
  const line = document.createElement("div");
  line.className = "log-line " + type;
  line.textContent = msg;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}
function clearLog() {
  const el = document.getElementById("progressLog");
  if (el) { el.innerHTML = ""; el.style.display = "none"; }
}

/* ── FORMAT HELPERS ─────────────────────────────────────── */
function fmtPrice(val) {
  if (val == null) return "--";
  const n = parseFloat(val);
  if (isNaN(n)) return String(val);
  if (n >= 1000)  return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (n >= 1)     return n.toFixed(4);
  if (n >= 0.01)  return n.toFixed(5);
  return n.toFixed(8);
}

function fmtChg(val) {
  if (val == null) return "--";
  const n = parseFloat(val);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function chgClass(val) {
  return parseFloat(val) >= 0 ? "pos" : "neg";
}

function verdictLabel(v) {
  return v === "strong" ? "STRONG BUY" : v === "moderate" ? "MODERATE" : "WEAK / SKIP";
}

function mlBadge(conf) {
  if (conf === null || conf === undefined) {
    return `<span class="ml-conf-badge none">ML: N/A</span>`;
  }
  const pct = Math.round(conf * 100);
  const cls = pct >= 70 ? "high" : pct >= 50 ? "medium" : "low";
  return `<span class="ml-conf-badge ${cls}">ML: ${pct}% confidence</span>`;
}

/* ── TICKER ─────────────────────────────────────────────── */
function renderTicker(coins) {
  const inner = document.getElementById("tickerInner");
  if (!inner || !coins.length) return;
  const items = [...coins, ...coins].map(c => {
    const chg = parseFloat(c.change_24h);
    return `<div class="ticker-item">
      <span class="t-sym">${c.symbol}</span>
      <span class="t-price">$${fmtPrice(c.price_usd)}</span>
      <span class="t-chg ${chgClass(chg)}">${fmtChg(chg)}</span>
    </div>`;
  }).join("");
  inner.innerHTML = items;
}

/* ── MOVER ROW ──────────────────────────────────────────── */
function moverRowHTML(coin, rank) {
  const sym = (coin.symbol || "??").substring(0, 5);
  return `
    <div class="mover-row">
      <span class="mover-rank">${rank}</span>
      <div class="coin-chip">${sym}</div>
      <div class="mover-info">
        <div class="mover-name">${coin.name || sym}</div>
        <div class="mover-sym">${coin.symbol || ""}</div>
      </div>
      <div class="mover-right">
        <div class="mover-price">$${fmtPrice(coin.price_usd)}</div>
        <div class="mover-chg ${chgClass(coin.change_24h)}">${fmtChg(coin.change_24h)}</div>
      </div>
    </div>`;
}

function renderMovers(gainers, losers) {
  let grid = document.getElementById("moversGrid");
  if (!grid) {
    const empty = document.querySelector(".empty-state");
    if (empty) {
      const div = document.createElement("div");
      div.id = "moversGrid"; div.className = "movers-grid";
      empty.replaceWith(div); grid = div;
    }
  }
  if (!grid) return;

  const gHTML = gainers.map((c, i) => moverRowHTML(c, i + 1)).join("");
  const lHTML = losers.map((c, i) => moverRowHTML(c, i + 1)).join("");

  grid.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
          Top Gainers
        </div>
        <span class="card-badge badge-green">24H</span>
      </div>
      ${gHTML || '<p style="color:var(--text-dim);font-size:12px;text-align:center;padding:20px">No gainers found</p>'}
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--red)" stroke-width="2.5" stroke-linecap="round"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>
          Top Losers
        </div>
        <span class="card-badge badge-red">24H</span>
      </div>
      ${lHTML || '<p style="color:var(--text-dim);font-size:12px;text-align:center;padding:20px">No losers found</p>'}
    </div>`;
}

/* ── PREDICTION CARD ────────────────────────────────────── */
function buildPredCard(p, idx) {
  const score    = parseInt(p.meta_score) || 50;
  const barCls   = score >= 70 ? "strong" : score >= 50 ? "moderate" : "weak";
  const bull     = parseInt(p.sentiment_bullish) || 50;
  const bear     = parseInt(p.sentiment_bearish) || 30;
  const neut     = Math.max(0, 100 - bull - bear);
  const sym      = (p.symbol || "??").substring(0, 5);
  const cat      = p.category || "crypto";
  const sourceBadge = cat === "forex" ? `<span class="card-badge badge-blue">FX</span>`
                    : cat === "commodity" ? `<span class="card-badge badge-gold">COMMODITY</span>`
                    : cat === "search" ? `<span class="card-badge badge-dim">SEARCHED</span>` : "";

  return `
    <div class="pred-card ${p.verdict}" style="animation-delay:${(idx || 0) * 0.06}s" id="pred-${p.prediction_id || ""}">
      <div class="pred-card-accent"></div>
      <div class="pred-card-body">
        <div class="pred-head">
          <div class="pred-coin-wrap">
            <div class="pred-coin-icon">${sym}</div>
            <div>
              <div class="pred-coin-name">${p.name || sym} ${sourceBadge}</div>
              <div class="pred-coin-sym">${p.symbol || ""}</div>
            </div>
          </div>
          <div class="verdict-tag ${p.verdict}">${verdictLabel(p.verdict)}</div>
        </div>

        <div class="meta-bar-wrap">
          <div class="meta-bar-labels"><span>META SCORE</span><span>${score}/100</span></div>
          <div class="meta-bar-track">
            <div class="meta-bar-fill ${barCls}" style="width:${score}%"></div>
          </div>
        </div>

        <div class="pred-data-grid">
          <div class="pred-data-cell"><div class="data-label">Price</div><div class="data-value">$${fmtPrice(p.price_usd)}</div></div>
          <div class="pred-data-cell"><div class="data-label">24H Change</div><div class="data-value ${parseFloat(p.change_24h) >= 0 ? 'green' : 'red'}">${fmtChg(p.change_24h)}</div></div>
          <div class="pred-data-cell"><div class="data-label">Entry</div><div class="data-value blue">$${fmtPrice(p.entry_low)}</div></div>
          <div class="pred-data-cell"><div class="data-label">Target</div><div class="data-value green">$${fmtPrice(p.target_price)}</div></div>
          <div class="pred-data-cell"><div class="data-label">Stop Loss</div><div class="data-value red">$${fmtPrice(p.stop_loss)}</div></div>
          <div class="pred-data-cell"><div class="data-label">Profit</div><div class="data-value gold">${p.profit_potential_min ? `${parseInt(p.profit_potential_min)}-${parseInt(p.profit_potential_max)}%` : "--"}</div></div>
        </div>

        <div class="sentiment-row">
          <span class="sent-label">SENTIMENT</span>
          <div class="sent-bar-wrap">
            <div class="sent-bar">
              <div class="sent-bull" style="width:${bull}%"></div>
              <div class="sent-neut" style="width:${neut}%"></div>
              <div class="sent-bear" style="width:${bear}%"></div>
            </div>
            <div class="sent-nums">
              <span class="bull">${bull}% BULL</span>
              <span class="neut">${neut}% NEUT</span>
              <span class="bear">${bear}% BEAR</span>
            </div>
          </div>
        </div>

        <div class="leverage-row">
          <div class="lev-info">
            <div class="lev-label">Recommended Leverage</div>
            <div class="lev-note">${p.leverage_note || "Futures/Margin only"}</div>
          </div>
          <div class="lev-value">${p.recommended_leverage || "1x"}</div>
        </div>

        <div class="ml-conf-row">${mlBadge(p.ml_confidence)}</div>

        ${p.summary ? `<div class="pred-summary">${p.summary}</div>` : ""}

        <div class="pred-actions">
          ${p.prediction_id ? `<a href="/predictions/${p.prediction_id}" class="btn btn-ghost btn-sm">Detail</a>` : ""}
          <a href="/outcomes/" class="btn btn-success btn-sm">Mark Outcome</a>
        </div>
      </div>
    </div>`;
}

function skeletonCard(symbol, name) {
  return `
    <div class="pred-card skeleton" id="skel-${symbol}">
      <div class="pred-card-accent"></div>
      <div class="pred-card-body">
        <div class="pred-head">
          <div class="pred-coin-wrap">
            <div class="pred-coin-icon">${symbol.substring(0,5)}</div>
            <div><div class="pred-coin-name">${name}</div><div class="pred-coin-sym">${symbol}</div></div>
          </div>
          <span class="skel-label">ANALYZING...</span>
        </div>
        <div class="skel-bar"></div>
        <div class="skel-bar short"></div>
        <div class="skel-bar"></div>
      </div>
    </div>`;
}

/* ── GLOBAL METRICS ─────────────────────────────────────── */
function renderMetrics(g, sessionId) {
  const el = document.getElementById("metricsStrip");
  if (!el || !g.total_market_cap) return;
  el.innerHTML = `
    <div class="stat-pill"><div class="stat-label">GLOBAL MCAP</div><div class="stat-value">$${(g.total_market_cap/1e12).toFixed(2)}T</div></div>
    <div class="stat-pill"><div class="stat-label">24H VOLUME</div><div class="stat-value">$${(g.total_volume_24h/1e9).toFixed(2)}B</div></div>
    <div class="stat-pill"><div class="stat-label">BTC DOM.</div><div class="stat-value gold">${parseFloat(g.btc_dominance).toFixed(1)}%</div></div>
    <div class="stat-pill"><div class="stat-label">SCAN</div><div class="stat-value">#${sessionId}</div></div>`;
}

/* ── MAIN SCAN FLOW ─────────────────────────────────────── */
let activeStream = null;

async function triggerScan() {
  const btn = document.getElementById("scanBtn");
  if (btn) btn.disabled = true;
  if (activeStream) { activeStream.close(); activeStream = null; }
  clearLog();
  setStatus("scanning", "Connecting to CoinMarketCap...");
  log("Fetching live market data...");

  let sessionId;
  try {
    const res  = await fetch("/scan/run", { method: "POST" });
    const data = await res.json();
    if (!data.ok) {
      setStatus("error", "Scan failed: " + (data.error || "Unknown error"));
      log("Error: " + (data.error || "Unknown"), "err");
      if (btn) btn.disabled = false; return;
    }
    sessionId = data.session_id;
    const allCoins = [...(data.gainers || []), ...(data.losers || [])];
    log(`CMC data loaded — ${allCoins.length} coins`, "ok");
    renderTicker(allCoins);
    renderMovers(data.gainers || [], data.losers || []);
    renderMetrics(data.global || {}, sessionId);

    // Show predictions section with skeletons
    const section = document.getElementById("predictionsSection");
    const grid    = document.getElementById("predsGrid");
    if (section) section.style.display = "";
    if (grid) grid.innerHTML = allCoins.map(c => skeletonCard(c.symbol, c.name)).join("");
    setStatus("scanning", `Scan #${sessionId} loaded. Starting AI analysis for ${allCoins.length} coins...`);
    log(`Starting Groq AI analysis stream for ${allCoins.length} coins...`);
  } catch (err) {
    setStatus("error", "Network error: " + err.message);
    log("Error: " + err.message, "err");
    if (btn) btn.disabled = false; return;
  }

  // SSE stream
  const es = new EventSource(`/scan/stream/${sessionId}`);
  activeStream = es;
  let completed = 0;

  es.onmessage = function(e) {
    let msg; try { msg = JSON.parse(e.data); } catch { return; }

    if (msg.type === "start") {
      log(`AI engine started — processing ${msg.total} coins`);
    } else if (msg.type === "analyzing") {
      setStatus("scanning", `Analyzing ${msg.current}/${msg.total}: ${msg.name} (${msg.symbol})...`);
      log(`Analyzing ${msg.symbol}...`);
    } else if (msg.type === "prediction") {
      completed++;
      const skel = document.getElementById(`skel-${msg.symbol}`);
      const card = buildPredCard(msg, completed);
      if (skel) skel.outerHTML = card;
      else { const g = document.getElementById("predsGrid"); if (g) g.insertAdjacentHTML("beforeend", card); }
      const cnt = document.getElementById("predCount");
      if (cnt) cnt.textContent = completed;
      log(`${msg.symbol} — ${(msg.verdict||"?").toUpperCase()} | score ${msg.meta_score}/100 | ${msg.recommended_leverage}`, "ok");
    } else if (msg.type === "coin_error") {
      const skel = document.getElementById(`skel-${msg.symbol}`);
      if (skel) skel.remove();
      log(`${msg.symbol} — analysis failed`, "warn");
    } else if (msg.type === "error") {
      setStatus("error", msg.message); es.close(); if (btn) btn.disabled = false;
    } else if (msg.type === "done") {
      es.close(); activeStream = null; if (btn) btn.disabled = false;
      const t = new Date().toUTCString().split(" ").slice(1,5).join(" ");
      setStatus("done", `Scan #${sessionId} complete — ${msg.completed}/${msg.total} predictions at ${t}`);
      log(`Done — ${msg.completed} predictions, ${msg.errors} errors`, "ok");
    }
  };

  es.onerror = function() {
    es.close(); activeStream = null; if (btn) btn.disabled = false;
    setStatus("error", "Connection lost. Check Predictions page for results.");
    log("SSE connection closed", "warn");
  };
}

/* ── SEARCH ─────────────────────────────────────────────── */
async function triggerSearch() {
  const input  = document.getElementById("searchInput");
  const grid   = document.getElementById("searchResults");
  const status = document.getElementById("searchStatus");
  const query  = input ? input.value.trim() : "";
  if (!query) return;

  if (status) { status.textContent = `Analyzing ${query}...`; status.style.color = "var(--text-dim)"; }
  if (grid) grid.innerHTML = skeletonCard(query.toUpperCase(), query);

  try {
    const res  = await fetch("/search/coin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    if (!data.ok) {
      if (status) { status.textContent = data.error || "Not found"; status.style.color = "var(--red)"; }
      if (grid) grid.innerHTML = "";
      return;
    }
    const p = { ...data.prediction, ...data.coin, prediction_id: data.prediction_id };
    if (grid) grid.innerHTML = buildPredCard(p, 0);
    if (status) { status.textContent = `Analysis complete for ${data.coin.name}`; status.style.color = "var(--green)"; }
  } catch (err) {
    if (status) { status.textContent = "Search failed: " + err.message; status.style.color = "var(--red)"; }
    if (grid) grid.innerHTML = "";
  }
}

// Search on Enter key
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("searchInput");
  if (input) {
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") triggerSearch();
    });
  }
});

/* ── SCREENSHOT-ASSISTED OUTCOME UPLOAD ───────────────────── */
async function handleScreenshotUpload(input) {
  const file = input.files[0];
  if (!file) return;

  const status = document.getElementById("screenshotStatus");
  const label  = document.getElementById("screenshotLabel");
  const zone   = document.getElementById("screenshotDropzone");

  if (status) {
    status.style.display = "block";
    status.style.color = "var(--text-dim)";
    status.textContent = "Reading screenshot with AI...";
  }
  if (label) label.textContent = "Analyzing " + file.name + "...";
  if (zone) zone.classList.add("loading");

  const formData = new FormData();
  formData.append("screenshot", file);

  try {
    const res  = await fetch("/outcomes/scan-screenshot", { method: "POST", body: formData });
    const data = await res.json();

    if (zone) zone.classList.remove("loading");

    if (!data.ok) {
      if (status) { status.style.color = "var(--red)"; status.textContent = data.error || "Could not read screenshot."; }
      if (label) label.textContent = "Click to upload your Bybit closed-trade screenshot — AI will read it and pre-fill the form below";
      return;
    }

    const ex = data.extracted;

    // Pre-fill form fields
    const resultSelect = document.getElementById("resultSelect");
    const pnlInput      = document.getElementById("pnlInput");
    const exitPriceInput= document.getElementById("exitPriceInput");
    const notesInput    = document.getElementById("notesInput");

    if (resultSelect && ex.result) resultSelect.value = ex.result;
    if (pnlInput && ex.pnl_pct !== null && ex.pnl_pct !== undefined) pnlInput.value = ex.pnl_pct;
    if (exitPriceInput && ex.exit_price !== null && ex.exit_price !== undefined) exitPriceInput.value = ex.exit_price;
    if (notesInput) {
      const parts = [];
      if (ex.symbol) parts.push(ex.symbol);
      if (ex.side) parts.push(ex.side);
      if (ex.notes) parts.push(ex.notes);
      notesInput.value = parts.join(" — ") + " (AI-read from screenshot, " + (ex.confidence || "medium") + " confidence)";
    }

    if (status) {
      status.style.color = "var(--green)";
      status.textContent = `AI read the screenshot (${ex.confidence || "medium"} confidence) — review the fields below and submit.`;
    }
    if (label) label.textContent = "Screenshot analyzed — " + file.name;

  } catch (err) {
    if (zone) zone.classList.remove("loading");
    if (status) { status.style.color = "var(--red)"; status.textContent = "Upload failed: " + err.message; }
    if (label) label.textContent = "Click to upload your Bybit closed-trade screenshot — AI will read it and pre-fill the form below";
  }
}

/* ── MOBILE SIDEBAR: close on outside click or nav item tap ──── */
document.addEventListener("click", (e) => {
  const sidebar = document.getElementById("sidebar");
  const toggle  = document.querySelector(".sidebar-toggle");
  if (!sidebar || !sidebar.classList.contains("open")) return;

  const clickedInsideSidebar = sidebar.contains(e.target);
  const clickedToggle        = toggle && toggle.contains(e.target);

  if (!clickedInsideSidebar && !clickedToggle) {
    sidebar.classList.remove("open");
  }
});

// Close drawer automatically when a nav link is tapped (mobile UX)
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sidebar .nav-item").forEach(link => {
    link.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      if (sidebar && window.innerWidth <= 900) sidebar.classList.remove("open");
    });
  });
});
