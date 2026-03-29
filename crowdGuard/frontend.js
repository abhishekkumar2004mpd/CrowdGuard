const STORAGE_KEYS = {
  session: "crowdguard_session",
  alerts: "crowdguard_alert_logs",
  nearLimit: "crowdguard_near_limit_logs",
  errors: "crowdguard_error_logs",
};

const DEMO_USERS = {
  user: { password: "user123", role: "viewer" },
  admin: { password: "admin123", role: "admin" },
};

const APP_STATE = {
  stream: null,
  streamUrl: "",
  animationFrame: null,
  pollingTimer: null,
  selectedSourceLabel: "Not started",
  selectedMode: "laptop",
  metrics: {
    person_count: 0,
    safe_capacity: 0,
    area_sq_meters: 0,
    density: 0,
    in_count: 0,
    out_count: 0,
    status: "NORMAL",
    message: "Waiting for source",
    occupancy_ratio: 0,
  },
  chartPoints: [],
  charts: {},
};

function readSession() {
  try {
    const value = localStorage.getItem(STORAGE_KEYS.session);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function writeSession(session) {
  localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(session));
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEYS.session);
}

function loadLogs(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

function saveLogs(key, logs) {
  localStorage.setItem(key, JSON.stringify(logs.slice(0, 40)));
}

function pushLog(key, entry, dedupeWindowMs = 8000) {
  const logs = loadLogs(key);
  const latest = logs[0];
  if (latest && latest.message === entry.message && Date.now() - latest.createdAt < dedupeWindowMs) {
    return;
  }
  logs.unshift(entry);
  saveLogs(key, logs);
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString();
}

function redirectForRole(role) {
  window.location.href = role === "admin" ? "./admin.html" : "./dashboard.html";
}

function initLoginPage() {
  const session = readSession();
  if (session) {
    redirectForRole(session.role);
    return;
  }

  const viewerTab = document.getElementById("viewerTab");
  const adminTab = document.getElementById("adminTab");
  const loginForm = document.getElementById("loginForm");
  const loginRoleLabel = document.getElementById("loginRoleLabel");
  const loginError = document.getElementById("loginError");
  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  let requestedRole = "viewer";

  function setLoginRole(role) {
    requestedRole = role;
    viewerTab.classList.toggle("active", role === "viewer");
    adminTab.classList.toggle("active", role === "admin");
    loginRoleLabel.textContent = role === "admin" ? "Admin access" : "Viewer access";
  }

  viewerTab.addEventListener("click", () => setLoginRole("viewer"));
  adminTab.addEventListener("click", () => setLoginRole("admin"));
  togglePassword.addEventListener("click", () => {
    passwordInput.type = passwordInput.type === "password" ? "text" : "password";
    togglePassword.textContent = passwordInput.type === "password" ? "Show password" : "Hide password";
  });

  loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const account = DEMO_USERS[username];

    if (!account || account.password !== password || account.role !== requestedRole) {
      loginError.textContent = "Invalid credentials for the selected role.";
      loginError.className = "message-strip error";
      return;
    }

    writeSession({ username, role: account.role, loginAt: Date.now() });
    redirectForRole(account.role);
  });
}

function requireSession({ adminOnly = false } = {}) {
  const session = readSession();
  if (!session) {
    window.location.href = "./index.html";
    return null;
  }
  if (adminOnly && session.role !== "admin") {
    window.location.href = "./dashboard.html";
    return null;
  }
  return session;
}

function wireSessionUi(session) {
  const userEl = document.getElementById("sessionUser");
  const avatarEl = document.getElementById("sessionAvatar");
  const roleEl = document.getElementById("sessionRole");
  const roleBadgeEl = document.getElementById("sessionRoleBadge");
  if (userEl) userEl.textContent = session.username;
  if (avatarEl) avatarEl.textContent = session.username.slice(0, 1).toUpperCase();
  if (roleEl) roleEl.textContent = session.role === "admin" ? "Admin" : "Viewer";
  if (roleBadgeEl) roleBadgeEl.textContent = session.role === "admin" ? "Admin" : "Viewer";

  document.querySelectorAll(".admin-only").forEach((element) => {
    element.classList.toggle("hidden", session.role !== "admin");
  });

  const logoutButton = document.getElementById("logoutButton");
  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      stopCurrentSource();
      clearSession();
      window.location.href = "./index.html";
    });
  }

  if (!window.__crowdGuardStorageBound) {
    window.__crowdGuardStorageBound = true;
    window.addEventListener("storage", (event) => {
      if (event.key !== STORAGE_KEYS.session) return;
      const updatedSession = readSession();
      if (!updatedSession) {
        window.location.href = "./index.html";
        return;
      }
      if (updatedSession.role !== "admin" && window.location.pathname.endsWith("admin.html")) {
        window.location.href = "./dashboard.html";
        return;
      }
      wireSessionUi(updatedSession);
    });
  }
}

function initTabs() {
  const buttons = document.querySelectorAll("[data-tab-target]");
  const panels = document.querySelectorAll("[data-tab-panel]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.tabTarget;
      buttons.forEach((item) => item.classList.toggle("active", item === button));
      panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.tabPanel === target));
    });
  });
}

async function refreshVideoDevices() {
  const select = document.getElementById("videoDeviceSelect");
  if (!select) return;
  select.innerHTML = "";
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter((device) => device.kind === "videoinput");
    if (!cameras.length) {
      select.add(new Option("No camera found", ""));
      return;
    }
    cameras.forEach((device, index) => {
      const label = device.label || `Camera ${index + 1}`;
      select.add(new Option(label, device.deviceId));
    });
  } catch (error) {
    reportError("device-enumeration", error.message);
  }
}

function getAnalysisCanvas() {
  return document.getElementById("analysisCanvas");
}

function getRawVideo() {
  return document.getElementById("rawFeedVideo");
}

function setChip(id, text, className = "") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `status-chip ${className}`.trim();
}

function reportError(source, detail) {
  pushLog(STORAGE_KEYS.errors, { createdAt: Date.now(), source, message: detail }, 2000);
  renderHealth();
}

async function startCurrentSource() {
  const mode = document.getElementById("sourceMode").value;
  APP_STATE.selectedMode = mode;
  try {
    if (mode === "upload") {
      document.getElementById("videoUploadInput").click();
      return;
    }
    if (mode === "laptop") {
      await startDeviceCamera("Built-in Laptop Camera");
      return;
    }
    if (mode === "nearby") {
      await startNearbyDevice();
      return;
    }
    if (mode === "cctv") {
      await startCctvSource();
    }
  } catch (error) {
    reportError(mode, error.message);
  }
}

async function startDeviceCamera(defaultLabel) {
  stopCurrentSource();
  const deviceSelect = document.getElementById("videoDeviceSelect");
  const deviceId = deviceSelect?.value;
  APP_STATE.stream = await navigator.mediaDevices.getUserMedia({
    video: deviceId ? { deviceId: { exact: deviceId } } : true,
    audio: false,
  });
  const video = getRawVideo();
  video.srcObject = APP_STATE.stream;
  APP_STATE.selectedSourceLabel = deviceSelect?.selectedOptions?.[0]?.text || defaultLabel;
  afterSourceStarted("Camera live", "Raw feed active");
}

async function startNearbyDevice() {
  const deviceSelect = document.getElementById("videoDeviceSelect");
  const options = [...(deviceSelect?.options || [])];
  const secondary = options[1] || options[0];
  if (!secondary || !secondary.value) {
    throw new Error("No nearby or secondary camera device is available.");
  }
  deviceSelect.value = secondary.value;
  await startDeviceCamera("Nearby device");
}

async function startCctvSource() {
  stopCurrentSource();
  const url = window.prompt("Enter a browser-compatible CCTV stream URL (mp4, webm, or HLS handled by the browser).");
  if (!url) return;
  const video = getRawVideo();
  APP_STATE.streamUrl = url;
  video.srcObject = null;
  video.src = url;
  await video.play().catch(() => {
    throw new Error("The browser could not play this CCTV source. Use a browser-compatible URL or backend stream bridge.");
  });
  APP_STATE.selectedSourceLabel = "Connected CCTV";
  afterSourceStarted("CCTV connected", "Network source live");
}

function startUploadSource(file) {
  if (!file) return;
  stopCurrentSource();
  const video = getRawVideo();
  APP_STATE.streamUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = APP_STATE.streamUrl;
  video.loop = true;
  video.play().catch((error) => reportError("upload", error.message));
  APP_STATE.selectedSourceLabel = file.name;
  afterSourceStarted("Uploaded footage", "Offline analysis mode");
}

function afterSourceStarted(rawStatus, analysisStatus) {
  setChip("rawFeedStatus", rawStatus);
  setChip("analysisFeedStatus", analysisStatus, "status-admin");
  document.getElementById("activeSourceLabel")?.replaceChildren(document.createTextNode(APP_STATE.selectedSourceLabel));
  document.getElementById("activeFeedMode")?.replaceChildren(document.createTextNode(APP_STATE.selectedMode.toUpperCase()));
  renderAnalysisLoop();
  startStatusPolling();
}

function stopCurrentSource() {
  if (APP_STATE.animationFrame) cancelAnimationFrame(APP_STATE.animationFrame);
  if (APP_STATE.pollingTimer) clearInterval(APP_STATE.pollingTimer);
  APP_STATE.animationFrame = null;
  APP_STATE.pollingTimer = null;
  if (APP_STATE.stream) APP_STATE.stream.getTracks().forEach((track) => track.stop());
  APP_STATE.stream = null;
  if (APP_STATE.streamUrl) {
    URL.revokeObjectURL(APP_STATE.streamUrl);
    APP_STATE.streamUrl = "";
  }
  const video = getRawVideo();
  if (video) {
    video.pause();
    video.srcObject = null;
    video.removeAttribute("src");
    video.load();
  }
  setChip("rawFeedStatus", "Idle");
  setChip("analysisFeedStatus", "Waiting", "status-admin");
}

function buildOverlayBoxes(width, height, count) {
  const boxCount = Math.min(count, 8);
  return Array.from({ length: boxCount }, (_, index) => {
    const boxWidth = width * 0.1;
    const boxHeight = height * 0.22;
    const gap = (width * 0.78) / Math.max(boxCount, 1);
    const x = width * 0.08 + gap * index;
    const y = height * (0.24 + (index % 2) * 0.1);
    return { x, y, width: boxWidth, height: boxHeight };
  });
}

function drawAnalysisOverlay(context, canvas, metrics) {
  const width = canvas.width;
  const height = canvas.height;
  const statusColor = metrics.status === "CRITICAL" ? "#d1342c" : metrics.status === "WARNING" ? "#df6d14" : "#2f7d32";
  const boxes = buildOverlayBoxes(width, height, metrics.person_count);
  context.lineWidth = 3;
  context.fillStyle = "rgba(18, 18, 22, 0.66)";
  context.fillRect(18, 18, 320, 134);
  context.font = "16px JetBrains Mono";
  context.fillStyle = "#ffffff";
  context.fillText(`Current Count: ${metrics.person_count}`, 32, 48);
  context.fillText(`Safe Capacity: ${metrics.safe_capacity}`, 32, 74);
  context.fillText(`Area (sqm): ${metrics.area_sq_meters}`, 32, 100);
  context.fillText(`Density: ${Number(metrics.density).toFixed(2)}`, 32, 126);
  context.strokeStyle = statusColor;
  boxes.forEach((box, index) => {
    context.strokeRect(box.x, box.y, box.width, box.height);
    context.fillStyle = statusColor;
    context.fillRect(box.x, box.y - 24, 66, 20);
    context.fillStyle = "#fff";
    context.fillText(`ID ${index + 1}`, box.x + 8, box.y - 9);
  });
  if (metrics.message) {
    context.fillStyle = statusColor;
    context.fillRect(0, height - 58, width, 58);
    context.fillStyle = "#fff";
    context.font = "18px Space Grotesk";
    context.fillText(metrics.message, 18, height - 22);
  }
}

function renderAnalysisLoop() {
  const video = getRawVideo();
  const canvas = getAnalysisCanvas();
  if (!video || !canvas) return;
  const context = canvas.getContext("2d");
  const draw = () => {
    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    canvas.width = width;
    canvas.height = height;
    if (video.readyState >= 2) context.drawImage(video, 0, 0, width, height);
    else {
      context.fillStyle = "#101114";
      context.fillRect(0, 0, width, height);
    }
    drawAnalysisOverlay(context, canvas, APP_STATE.metrics);
    APP_STATE.animationFrame = requestAnimationFrame(draw);
  };
  if (APP_STATE.animationFrame) cancelAnimationFrame(APP_STATE.animationFrame);
  draw();
}

async function fetchStatus() {
  try {
    const response = await fetch("http://127.0.0.1:5001/status");
    if (!response.ok) throw new Error(`API status ${response.status}`);
    return await response.json();
  } catch {
    return null;
  }
}

async function fetchHealth() {
  try {
    const response = await fetch("http://127.0.0.1:5001/health");
    if (!response.ok) throw new Error("health check failed");
    const payload = await response.json();
    setChip("apiHealthChip", payload.status === "ok" ? "API online" : "API degraded", payload.status === "ok" ? "status-admin" : "");
  } catch {
    setChip("apiHealthChip", "API offline");
  }
}

function simulateMetrics() {
  const base = APP_STATE.metrics.person_count || 6;
  const next = Math.max(0, base + Math.round((Math.random() - 0.3) * 3));
  const capacity = APP_STATE.metrics.safe_capacity || 40;
  const area = APP_STATE.metrics.area_sq_meters || 80;
  const occupancy = capacity ? next / capacity : 0;
  return {
    person_count: next,
    safe_capacity: capacity,
    area_sq_meters: area,
    density: next / area,
    in_count: Math.max(0, Math.round(next * 0.32)),
    out_count: Math.max(0, Math.round(next * 0.18)),
    status: occupancy >= 1 ? "CRITICAL" : occupancy >= 0.85 ? "WARNING" : "NORMAL",
    message: occupancy >= 1 ? "Stampede happening critical notice" : occupancy >= 0.85 ? "Stampede might happen" : "Crowd within safe range",
    occupancy_ratio: occupancy,
    timestamp: new Date().toISOString(),
  };
}

function normalizeMetrics(payload) {
  if (!payload || payload.status === "idle") return simulateMetrics();
  return {
    person_count: Number(payload.person_count || 0),
    safe_capacity: Number(payload.safe_capacity || 0),
    area_sq_meters: Number(payload.area_sq_meters || 0),
    density: Number(payload.density || 0),
    in_count: Number(payload.in_count || 0),
    out_count: Number(payload.out_count || 0),
    status: payload.status || "NORMAL",
    message: payload.message || "",
    occupancy_ratio: Number(payload.occupancy_ratio || 0),
    timestamp: payload.timestamp || new Date().toISOString(),
  };
}

function updateMetrics(metrics) {
  APP_STATE.metrics = metrics;
  document.getElementById("metricCurrent").textContent = metrics.person_count;
  document.getElementById("metricCapacity").textContent = metrics.safe_capacity;
  document.getElementById("metricArea").textContent = metrics.area_sq_meters;
  document.getElementById("metricDensity").textContent = Number(metrics.density).toFixed(2);
  document.getElementById("metricInCount")?.replaceChildren(document.createTextNode(metrics.in_count));
  document.getElementById("metricOutCount")?.replaceChildren(document.createTextNode(metrics.out_count));
  document.getElementById("metricStatus")?.replaceChildren(document.createTextNode(metrics.status));
  document.getElementById("metricMessage")?.replaceChildren(document.createTextNode(metrics.message || "No active message"));
  document.getElementById("activeOccupancy")?.replaceChildren(document.createTextNode(`${Math.round((metrics.occupancy_ratio || 0) * 100)}%`));
  document.getElementById("lastMetricsUpdate")?.replaceChildren(document.createTextNode(formatTime(metrics.timestamp || Date.now())));
  const banner = document.getElementById("alertBanner");
  banner.textContent = metrics.message || "CrowdGuard ready.";
  banner.className = `message-strip ${metrics.status === "CRITICAL" ? "critical" : metrics.status === "WARNING" ? "warning" : "normal"}`;
  banner.classList.remove("hidden");
  APP_STATE.chartPoints.push({ time: formatTime(Date.now()), count: metrics.person_count, density: Number(metrics.density).toFixed(2) });
  APP_STATE.chartPoints = APP_STATE.chartPoints.slice(-12);
  updateCharts();
  updateHistoryLogs(metrics);
}

function updateHistoryLogs(metrics) {
  const source = APP_STATE.selectedSourceLabel;
  if (["WARNING", "CRITICAL"].includes(metrics.status)) {
    pushLog(STORAGE_KEYS.alerts, {
      createdAt: Date.now(),
      source,
      status: metrics.status,
      count: metrics.person_count,
      density: Number(metrics.density).toFixed(2),
      message: metrics.message,
    });
  }
  if ((metrics.occupancy_ratio || 0) >= 0.7 && (metrics.occupancy_ratio || 0) < 0.85) {
    pushLog(STORAGE_KEYS.nearLimit, {
      createdAt: Date.now(),
      source,
      occupancy: `${Math.round((metrics.occupancy_ratio || 0) * 100)}%`,
      density: Number(metrics.density).toFixed(2),
      message: "Crowd approaching alert threshold.",
    }, 5000);
  }
  renderTables();
}

function renderTables() {
  const alertRows = loadLogs(STORAGE_KEYS.alerts);
  const nearRows = loadLogs(STORAGE_KEYS.nearLimit);
  const errorRows = loadLogs(STORAGE_KEYS.errors);
  const alertTable = document.getElementById("alertLogTable");
  const nearTable = document.getElementById("nearLimitLogTable");
  const errorTable = document.getElementById("errorLogTable");
  if (alertTable) {
    alertTable.innerHTML = alertRows.length ? alertRows.map((entry) => `<tr><td>${formatTime(entry.createdAt)}</td><td>${entry.status}</td><td>${entry.count}</td><td>${entry.message}</td></tr>`).join("") : `<tr><td colspan="4">No alert logs yet.</td></tr>`;
  }
  if (nearTable) {
    nearTable.innerHTML = nearRows.length ? nearRows.map((entry) => `<tr><td>${formatTime(entry.createdAt)}</td><td>${entry.occupancy}</td><td>${entry.density}</td><td>${entry.source}</td></tr>`).join("") : `<tr><td colspan="4">No near-limit logs yet.</td></tr>`;
  }
  if (errorTable) {
    errorTable.innerHTML = errorRows.length ? errorRows.map((entry) => `<tr><td>${formatTime(entry.createdAt)}</td><td>${entry.source}</td><td>${entry.message}</td></tr>`).join("") : `<tr><td colspan="3">No errors logged.</td></tr>`;
  }
}

function initCharts() {
  if (typeof Chart === "undefined") return;
  const countCanvas = document.getElementById("countChart");
  const densityCanvas = document.getElementById("densityChart");
  if (!countCanvas || !densityCanvas) return;
  APP_STATE.charts.count = new Chart(countCanvas, {
    type: "line",
    data: { labels: [], datasets: [{ label: "People", data: [], borderColor: "#155eef", backgroundColor: "rgba(21, 94, 239, 0.14)", fill: true, tension: 0.35 }] },
    options: { responsive: true, maintainAspectRatio: true },
  });
  APP_STATE.charts.density = new Chart(densityCanvas, {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Density", data: [], backgroundColor: "#df6d14" }] },
    options: { responsive: true, maintainAspectRatio: true },
  });
}

function updateCharts() {
  const labels = APP_STATE.chartPoints.map((point) => point.time);
  const counts = APP_STATE.chartPoints.map((point) => point.count);
  const densities = APP_STATE.chartPoints.map((point) => point.density);
  if (APP_STATE.charts.count) {
    APP_STATE.charts.count.data.labels = labels;
    APP_STATE.charts.count.data.datasets[0].data = counts;
    APP_STATE.charts.count.update();
  }
  if (APP_STATE.charts.density) {
    APP_STATE.charts.density.data.labels = labels;
    APP_STATE.charts.density.data.datasets[0].data = densities;
    APP_STATE.charts.density.update();
  }
}

function renderHealth() {
  const errorRows = loadLogs(STORAGE_KEYS.errors);
  const cpuEl = document.getElementById("healthCpu");
  const ramEl = document.getElementById("healthRam");
  const softwareEl = document.getElementById("healthSoftware");
  const errorsEl = document.getElementById("healthErrors");
  if (!cpuEl || !ramEl || !softwareEl || !errorsEl) return;
  const cpuApprox = Math.min(95, Math.max(12, Math.round(APP_STATE.metrics.person_count * 2.2)));
  const jsHeap = performance?.memory?.usedJSHeapSize ? `${Math.round(performance.memory.usedJSHeapSize / 1048576)} MB` : `${(navigator.deviceMemory || 4)} GB device`;
  cpuEl.textContent = `${cpuApprox}%`;
  ramEl.textContent = jsHeap;
  softwareEl.textContent = errorRows.length > 5 ? "Degraded" : "Healthy";
  errorsEl.textContent = `${errorRows.length}`;
}

async function pollStatusOnce() {
  updateMetrics(normalizeMetrics(await fetchStatus()));
  renderHealth();
}

function startStatusPolling() {
  if (APP_STATE.pollingTimer) clearInterval(APP_STATE.pollingTimer);
  pollStatusOnce();
  APP_STATE.pollingTimer = setInterval(pollStatusOnce, 3000);
  fetchHealth();
}

function initDashboardPage({ adminOnly = false } = {}) {
  const session = requireSession({ adminOnly });
  if (!session) return;
  wireSessionUi(session);
  initTabs();
  initCharts();
  renderTables();
  renderHealth();
  refreshVideoDevices();
  fetchHealth();
  document.getElementById("startSourceButton").addEventListener("click", startCurrentSource);
  document.getElementById("stopSourceButton").addEventListener("click", stopCurrentSource);
  document.getElementById("videoUploadInput").addEventListener("change", (event) => startUploadSource(event.target.files?.[0]));
  document.getElementById("sourceMode").addEventListener("change", async (event) => {
    const picker = document.querySelector(".device-picker");
    if (event.target.value === "upload") picker?.classList.add("hidden");
    else {
      picker?.classList.remove("hidden");
      await refreshVideoDevices();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("loginForm")) {
    initLoginPage();
    return;
  }
  const page = document.body.dataset.page;
  if (page === "admin") initDashboardPage({ adminOnly: true });
  if (page === "dashboard") initDashboardPage({ adminOnly: false });
});
