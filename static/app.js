"use strict";

let baths       = [];
let editMode    = false;
let currentId   = null;
let lastUpdated = null; // 最後に取得したタイムスタンプ

// ドラッグ状態
let drag = {
  active: false,
  bathId: null,
  el: null,
  startX: 0, startY: 0,
  origLeft: 0, origTop: 0,
  moved: false,
};

// ── データ取得 ────────────────────────────────────
async function load() {
  const res  = await fetch("/api/baths");
  const data = await res.json();
  baths = data.baths;
  lastUpdated = data.last_updated ?? null;
  renderPins();
  renderSVG();
  renderAmbient(data.gateway);
  renderLastUpdated(data.last_updated);
}

// ── 更新時刻表示 ──────────────────────────────────
function renderLastUpdated(isoStr) {
  const el = document.getElementById("last-update");
  if (!el) return;
  if (!isoStr) { el.textContent = ""; return; }
  const d = new Date(isoStr);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  el.textContent = `更新 ${hh}:${mm}:${ss}`;
}

// ── 差分チェック（5秒ごと）────────────────────────
async function checkUpdates() {
  try {
    const res  = await fetch("/api/baths");
    const data = await res.json();
    if (data.last_updated && data.last_updated !== lastUpdated) {
      // タイムスタンプが変わった → 画面を更新
      baths = data.baths;
      lastUpdated = data.last_updated;
      renderPins();
      renderSVG();
      renderAmbient(data.gateway);
      renderLastUpdated(data.last_updated);
      // ↻ボタンが待機中なら解除
      const btn = document.getElementById("fetch-btn");
      if (btn.disabled) {
        btn.textContent = "↻";
        btn.disabled = false;
      }
    }
  } catch {}
}

// ── 外気温（ゲートウェイ）表示 ───────────────────────
function renderAmbient(gateway) {
  const el = document.getElementById("ambient-display");
  if (!gateway || gateway.temp === null || gateway.temp === undefined) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  document.getElementById("ambient-temp").textContent =
    Number(gateway.temp).toFixed(1) + "℃";
  const humEl = document.getElementById("ambient-humidity");
  if (gateway.humidity !== null && gateway.humidity !== undefined) {
    humEl.textContent = "💧" + Number(gateway.humidity).toFixed(1) + "%";
    humEl.style.display = "";
  } else {
    humEl.textContent = "";
  }
}

// ── ピン描画 ──────────────────────────────────────
function renderPins() {
  const container = document.getElementById("pins");
  container.innerHTML = baths.map(b => {
    const hasTemp  = b.temp !== null && b.temp !== undefined;
    const tempHtml = hasTemp
      ? `<span class="pin-temp">${Number(b.temp).toFixed(1)}<span class="pin-unit">℃</span></span>`
      : `<span class="pin-temp no-data">-- ℃</span>`;
    const targetHtml   = b.target ? `<div class="pin-target">${b.target}</div>` : "";
    const humidityHtml = (b.humidity !== null && b.humidity !== undefined)
      ? `<div class="pin-humidity">&#128167; ${Number(b.humidity).toFixed(1)}%</div>` : "";

    return `
      <div class="bath-pin color-${b.color}"
           id="pin-${b.id}"
           style="left:${b.left}%;top:${b.top}%"
           data-id="${b.id}">
        <div class="pin-card">
          <div class="edit-badge">+</div>
          <div class="pin-name">${b.name}</div>
          ${targetHtml}
          ${tempHtml}
          ${humidityHtml}
          <div class="pin-hint">${editMode ? "ドラッグで移動" : "タップして入力"}</div>
        </div>
        <div class="pin-pole"></div>
        <div class="pin-shadow"></div>
      </div>`;
  }).join("");

  // イベント登録
  for (const b of baths) {
    const el = document.getElementById(`pin-${b.id}`);
    el.addEventListener("pointerdown", onPointerDown);
  }
}

// ── SVG描画 ───────────────────────────────────────
function renderSVG() {
  const svg = document.getElementById("map-svg");
  const W = svg.clientWidth  || 900;
  const H = svg.clientHeight || 400;

  const px = (lp, tp) => [W * lp / 100, H * tp / 100];
  const centers = {};
  for (const b of baths) centers[b.id] = px(b.left, b.top);

  const connections = [[1,2],[2,3],[3,4],[4,6],[6,5],[3,5],[5,7],[2,7]];

  let lines = connections.map(([a, b]) => {
    const [ax, ay] = centers[a] || [0,0];
    const [bx, by] = centers[b] || [0,0];
    const mx = (ax+bx)/2, my = (ay+by)/2 - 15;
    return `<path d="M${ax},${ay} Q${mx},${my} ${bx},${by}"
      stroke="rgba(255,255,255,0.07)" stroke-width="1.5"
      stroke-dasharray="4 5" fill="none"/>`;
  }).join("");

  let dots = baths.map(b => {
    const [cx, cy] = centers[b.id];
    return `<circle cx="${cx}" cy="${cy}" r="4"
      fill="rgba(255,255,255,0.15)"
      filter="url(#dot-glow)"/>`;
  }).join("");

  svg.innerHTML = `
    <defs>
      <filter id="dot-glow">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="bgGrad" cx="40%" cy="40%" r="65%">
        <stop offset="0%"   stop-color="rgba(255,255,255,0.03)"/>
        <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
      </radialGradient>
    </defs>
    <path d="M${W*.04},${H*.55}
      C${W*.05},${H*.35} ${W*.07},${H*.22} ${W*.13},${H*.15}
      C${W*.18},${H*.08} ${W*.25},${H*.04} ${W*.35},${H*.08}
      L${W*.50},${H*.06} C${W*.62},${H*.02} ${W*.72},${H*.0} ${W*.80},${H*.05}
      L${W*.88},${H*.14} L${W*.88},${H*.78}
      L${W*.68},${H*.84} L${W*.44},${H*.88}
      L${W*.20},${H*.80} Z"
      fill="url(#bgGrad)"
      stroke="rgba(255,255,255,0.045)" stroke-width="1.5"/>
    ${lines}${dots}`;
}

// ── ドラッグ処理 ──────────────────────────────────
function onPointerDown(e) {
  if (e.button !== 0 && e.pointerType === "mouse") return;
  const el = e.currentTarget;
  const id = Number(el.dataset.id);
  const bath = baths.find(b => b.id === id);

  drag = {
    active: true, bathId: id, el,
    startX: e.clientX, startY: e.clientY,
    origLeft: bath.left, origTop: bath.top,
    moved: false,
  };

  el.setPointerCapture(e.pointerId);
  el.addEventListener("pointermove", onPointerMove);
  el.addEventListener("pointerup",   onPointerUp);
  e.preventDefault();
}

function onPointerMove(e) {
  if (!drag.active) return;
  const dx = e.clientX - drag.startX;
  const dy = e.clientY - drag.startY;
  if (!drag.moved && Math.hypot(dx, dy) > 6) drag.moved = true;
  if (!drag.moved) return;

  if (!editMode) return; // 編集モードでないと移動しない

  const container = document.getElementById("map-container");
  const rect = container.getBoundingClientRect();
  const newLeft = drag.origLeft + (dx / rect.width)  * 100;
  const newTop  = drag.origTop  + (dy / rect.height) * 100;

  const left = Math.max(5, Math.min(93, newLeft));
  const top  = Math.max(5, Math.min(90, newTop));

  drag.el.style.left = left + "%";
  drag.el.style.top  = top  + "%";
  drag.el.classList.add("dragging");

  // SVGも追従
  const b = baths.find(b => b.id === drag.bathId);
  b.left = left;
  b.top  = top;
  renderSVG();
}

async function onPointerUp(e) {
  drag.el.removeEventListener("pointermove", onPointerMove);
  drag.el.removeEventListener("pointerup",   onPointerUp);
  drag.el.classList.remove("dragging");

  if (drag.moved && editMode) {
    // 位置を保存
    const b = baths.find(b => b.id === drag.bathId);
    await fetch(`/api/position/${drag.bathId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ left: b.left, top: b.top }),
    });
  } else if (!drag.moved) {
    // タップ → 温度入力
    if (!editMode) openDialog(drag.bathId);
  }

  drag.active = false;
}

// ── 編集モード切替 ────────────────────────────────
function toggleEdit() {
  editMode = !editMode;
  document.body.classList.toggle("edit-mode", editMode);
  document.getElementById("edit-btn").classList.toggle("active", editMode);
  document.getElementById("header-sub").textContent =
    editMode ? "ドラッグで湯舟を移動できます" : "各湯舟をタップして温度を入力";
  renderPins();
}

// ── ダイアログ ────────────────────────────────────
function openDialog(id) {
  currentId = id;
  const bath = baths.find(b => b.id === id);
  document.getElementById("dialog-title").textContent  = bath.name;
  document.getElementById("dialog-target").textContent =
    bath.target ? `目安温度: ${bath.target}` : "";
  document.getElementById("temp-input").value = bath.temp ?? "";
  document.getElementById("overlay").classList.remove("hidden");
  setTimeout(() => document.getElementById("temp-input").focus(), 50);
}

function closeDialog() {
  document.getElementById("overlay").classList.add("hidden");
  currentId = null;
}

async function saveTemp() {
  const val = document.getElementById("temp-input").value;
  if (val === "") return;
  const temp = parseFloat(val);
  if (isNaN(temp)) return;
  await fetch(`/api/temp/${currentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temp }),
  });
  closeDialog();
  load();
}

async function clearTemp() {
  await fetch(`/api/temp/${currentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temp: null }),
  });
  closeDialog();
  load();
}

document.getElementById("temp-input").addEventListener("keydown", e => {
  if (e.key === "Enter")  saveTemp();
  if (e.key === "Escape") closeDialog();
});
document.getElementById("overlay").addEventListener("click", e => {
  if (e.target === document.getElementById("overlay")) closeDialog();
});

// ── 背景写真アップロード ──────────────────────────
async function uploadPhoto(input) {
  const file = input.files[0];
  if (!file) return;

  document.getElementById("converting-overlay").classList.remove("hidden");

  const form = new FormData();
  form.append("photo", file);
  form.append("use_api", "0"); // ローカル変換。Replicate使う場合は "1"

  try {
    const res = await fetch("/api/bg/upload", { method: "POST", body: form });
    const data = await res.json();
    if (data.ok) {
      applyBackground(data.bg + "?t=" + Date.now());
    } else {
      alert("変換エラー: " + data.error);
    }
  } catch(e) {
    alert("通信エラー: " + e);
  } finally {
    document.getElementById("converting-overlay").classList.add("hidden");
    input.value = "";
  }
}

function applyBackground(url) {
  const floor = document.querySelector(".map-floor");
  floor.style.backgroundImage = `url('${url}')`;
  floor.style.backgroundSize  = "cover";
  floor.style.backgroundPosition = "center";
  // グリッドを薄くして写真を見やすく
  floor.style.setProperty("--grid-opacity", "0.6");
}

// 起動時に既存の背景があれば適用
async function checkBg() {
  const res  = await fetch("/api/bg/status");
  const data = await res.json();
  if (data.exists) applyBackground("/static/bg.png?t=" + Date.now());
}

// ── ADB状態確認・手動取得 ────────────────────────────
async function checkAdbStatus() {
  try {
    const res  = await fetch("/api/adb/status");
    const data = await res.json();
    const badge = document.getElementById("adb-badge");
    badge.hidden = !data.running;
  } catch {}
}

async function fetchNow() {
  const btn = document.getElementById("fetch-btn");
  btn.textContent = "…";
  btn.disabled = true;
  try {
    await fetch("/api/adb/fetch", { method: "POST" });
    // checkUpdates() が5秒ごとにタイムスタンプを監視し、
    // 更新を検知したら自動的にボタンを解除・画面更新する
  } catch {
    btn.textContent = "↻";
    btn.disabled = false;
  }
}

// 5秒ごとに更新チェック（タイムスタンプが変わったら即座に画面更新）
setInterval(checkUpdates, 10000);
// ADB状態を10秒ごとに確認
setInterval(checkAdbStatus, 10000);

window.addEventListener("resize", renderSVG);
checkBg();
checkAdbStatus();
load();
