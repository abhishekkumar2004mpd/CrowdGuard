import { useEffect, useMemo, useRef, useState } from "react";

const STORAGE_KEY = "crowdguard_react_session";
const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5001"
).replace(/\/$/, "");
const DEFAULT_ADMIN_EMAIL = "2306252@kiit.ac.in";

const EMPTY_METRICS = {
  person_count: 0,
  safe_capacity: 0,
  area_sq_meters: 0,
  density: 0,
  in_count: 0,
  out_count: 0,
  status: "IDLE",
  message: "Backend model is offline or has not published frames yet.",
  occupancy_ratio: 0,
  timestamp: new Date().toISOString(),
};

function readStored(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function writeStored(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function usePersistentState(key, initialValue) {
  const [value, setValue] = useState(() => readStored(key, initialValue));
  useEffect(() => {
    writeStored(key, value);
  }, [key, value]);
  return [value, setValue];
}

function timeText(value) {
  return new Date(value).toLocaleTimeString();
}

async function apiJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || "Request failed.");
  }
  return payload;
}

function App() {
  const [session, setSession] = usePersistentState(STORAGE_KEY, null);
  const normalizedSession = session
    ? {
        name: session.name || session.username || "CrowdCtrl User",
        email: session.email || "",
        role: session.role || "viewer",
        loginAt: session.loginAt || Date.now(),
      }
    : null;

  if (!normalizedSession) {
    return <LoginScreen onSession={setSession} />;
  }

  return <Dashboard session={normalizedSession} onLogout={() => setSession(null)} />;
}

function LoginScreen({ onSession }) {
  const [view, setView] = useState("signin");
  const [role, setRole] = useState("viewer");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [forgotEmail, setForgotEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const submitLogin = async () => {
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const payload = await apiJson("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.email,
          password: form.password,
        }),
      });
      onSession({ ...payload.user, loginAt: Date.now() });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const requestAccess = async () => {
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const payload = await apiJson("/auth/request-access", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          password: form.password,
        }),
      });
      setMessage(payload.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const submitSignup = async () => {
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const payload = await apiJson("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          password: form.password,
          role,
        }),
      });
      setMessage(`${payload.user.role === "admin" ? "Admin" : "Viewer"} account created. You can sign in now.`);
      setView("signin");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const forgotPassword = async () => {
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const payload = await apiJson("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: forgotEmail }),
      });
      setMessage(payload.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-shell">
      <section className="login-brand-panel">
        <h1 className="brand-title">
          <span className="brand-title-crowd">Crowd</span>
          <span className="brand-title-guard">Ctrl</span>
        </h1>
      </section>

      <section className="login-card glass-card">
        <div className="mode-switch dual role-switch" data-active={role}>
          <button className={role === "viewer" ? "active" : ""} onClick={() => setRole("viewer")}>Viewer</button>
          <button className={role === "admin" ? "active" : ""} onClick={() => setRole("admin")}>Admin</button>
        </div>

        <div className="mode-switch triple auth-switch" data-active={view}>
          <button className={view === "signin" ? "active" : ""} onClick={() => setView("signin")}>Sign in</button>
          <button className={view === "signup" ? "active" : ""} onClick={() => setView("signup")}>Sign up</button>
          <button className={view === "forgot" ? "active" : ""} onClick={() => setView("forgot")}>Forgot Password</button>
        </div>

        {view !== "forgot" ? (
          <>
            {view === "signup" ? (
              <div className="field">
                <label>Full Name</label>
                <input value={form.name} onChange={(event) => setField("name", event.target.value)} />
              </div>
            ) : null}
            <div className="field">
              <label>Email</label>
              <input value={form.email} onChange={(event) => setField("email", event.target.value)} placeholder="name@example.com" />
            </div>
            <div className="field">
              <label>Password</label>
              <div className="password-row">
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={(event) => setField("password", event.target.value)}
                />
                <button
                  className={`visibility-toggle ${showPassword ? "active" : ""}`}
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((prev) => !prev)}
                >
                  <span className="visibility-track">
                    <span className="visibility-thumb" />
                  </span>
                </button>
              </div>
            </div>
            {view === "signin" ? (
              <button className="primary" onClick={submitLogin} disabled={submitting}>
                {submitting ? "Signing In..." : "Enter CrowdCtrl"}
              </button>
            ) : (
              <button className="primary" onClick={submitSignup} disabled={submitting}>
                {submitting ? "Creating..." : `Create ${role === "admin" ? "Admin" : "Viewer"} Account`}
              </button>
            )}
          </>
        ) : (
          <>
            <div className="field">
              <label>Account Email</label>
              <input value={forgotEmail} onChange={(event) => setForgotEmail(event.target.value)} placeholder="name@example.com" />
            </div>
            <button className="primary" onClick={forgotPassword} disabled={submitting}>
              {submitting ? "Sending..." : "Send Reset Request"}
            </button>
            <p className="helper-text">CrowdCtrl will notify the default admin mail: {DEFAULT_ADMIN_EMAIL}</p>
          </>
        )}

        {message ? <div className="banner neutral">{message}</div> : null}
        {error ? <div className="banner critical">{error}</div> : null}
      </section>
    </div>
  );
}

function Dashboard({ session, onLogout }) {
  const [tab, setTab] = useState("overview");
  const [sourceMode, setSourceMode] = useState("camera");
  const [backendSources, setBackendSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [sourceHint, setSourceHint] = useState("Pick a backend-visible camera or switch to CCTV/upload.");
  const [apiOnline, setApiOnline] = useState(false);
  const [metrics, setMetrics] = useState(EMPTY_METRICS);
  const [activeSourceLabel, setActiveSourceLabel] = useState("Not started");
  const [rawFeedStatus, setRawFeedStatus] = useState("Idle");
  const [analysisFeedStatus, setAnalysisFeedStatus] = useState("Waiting");
  const [rawFrameReady, setRawFrameReady] = useState(false);
  const [analysisFrameReady, setAnalysisFrameReady] = useState(false);
  const [chartPoints, setChartPoints] = useState([]);
  const [alertLogs, setAlertLogs] = useState([]);
  const [metricSnapshots, setMetricSnapshots] = useState([]);
  const [errorLogs, setErrorLogs] = useState([]);
  const [passwordResetLogs, setPasswordResetLogs] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);

  const rawImageRef = useRef(null);
  const analysisImageRef = useRef(null);
  const uploadRef = useRef(null);
  const frameTimerRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    fetch(`${API_BASE}/control/discover`)
      .then((response) => response.json())
      .then((payload) => {
        if (!mounted) return;
        const sources = payload.sources || [];
        setBackendSources(sources);
        const firstCamera = sources.find((item) => item.kind === "camera");
        if (firstCamera) {
          setSelectedSourceId(firstCamera.camera_id);
          setSourceMode(firstCamera.kind);
          setSourceHint(`Backend will open ${firstCamera.label} at ${firstCamera.resolution}.`);
        } else {
          setSourceHint("No backend webcam was discovered. Use CCTV or upload footage instead.");
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const statusTimer = setInterval(async () => {
      try {
        const health = await apiJson("/health");
        setApiOnline(health.status === "ok");
      } catch {
        setApiOnline(false);
      }

      try {
        const payload = await apiJson("/status", { headers: {} });
        const nextMetrics = payload.status === "idle" ? EMPTY_METRICS : {
          ...EMPTY_METRICS,
          ...payload,
          occupancy_ratio: Number(payload.occupancy_ratio || 0),
          density: Number(payload.density || 0),
          person_count: Number(payload.person_count || 0),
          safe_capacity: Number(payload.safe_capacity || 0),
          area_sq_meters: Number(payload.area_sq_meters || 0),
          in_count: Number(payload.in_count || 0),
          out_count: Number(payload.out_count || 0),
        };
        setMetrics(nextMetrics);
        setChartPoints((prev) => [...prev.slice(-11), {
          time: timeText(Date.now()),
          count: nextMetrics.person_count,
          density: nextMetrics.density,
        }]);
      } catch {
        setMetrics(EMPTY_METRICS);
      }

      try {
        const control = await apiJson("/control/state", { headers: {} });
        if (control.running && control.source?.label) {
          setActiveSourceLabel(control.source.label);
          setRawFeedStatus("Backend raw feed live");
          setAnalysisFeedStatus("Backend model live");
        } else {
          setRawFeedStatus("Idle");
          setAnalysisFeedStatus("Waiting");
          setRawFrameReady(false);
          setAnalysisFrameReady(false);
        }
      } catch {
        // keep previous state
      }

    }, 1000);

    const logTimer = setInterval(async () => {
      try {
        const [alerts, snapshots, errors, resets] = await Promise.all([
          apiJson("/logs/alerts"),
          apiJson("/logs/metrics"),
          apiJson("/logs/errors"),
          apiJson("/logs/password_resets"),
        ]);
        setAlertLogs(alerts.items || []);
        setMetricSnapshots(snapshots.items || []);
        setErrorLogs(errors.items || []);
        setPasswordResetLogs(resets.items || []);
      } catch {
        // ignore transient log polling issues
      }

      if (session.role === "admin") {
        try {
          const pending = await apiJson("/auth/pending-viewers");
          setPendingUsers(pending.items || []);
        } catch {
          setPendingUsers([]);
        }
      }
    }, 5000);

    return () => {
      clearInterval(statusTimer);
      clearInterval(logTimer);
    };
  }, [session.role]);

  useEffect(() => {
    const refreshFrames = () => {
      if (document.hidden) {
        return;
      }
      if (rawImageRef.current) {
        rawImageRef.current.src = `${API_BASE}/frame/raw?ts=${Date.now()}`;
      }
      if (analysisImageRef.current) {
        analysisImageRef.current.src = `${API_BASE}/frame/annotated?ts=${Date.now()}`;
      }
    };

    refreshFrames();
    frameTimerRef.current = setInterval(refreshFrames, 250);

    return () => {
      if (frameTimerRef.current) {
        clearInterval(frameTimerRef.current);
      }
    };
  }, []);

  const summary = useMemo(() => {
    const cpu = `${Math.min(95, Math.max(10, metrics.person_count * 2))}%`;
    const ram = performance?.memory?.usedJSHeapSize
      ? `${Math.round(performance.memory.usedJSHeapSize / 1048576)} MB`
      : `${navigator.deviceMemory || 4} GB device`;
    const software = errorLogs.length > 5 ? "Degraded" : "Healthy";
    return { cpu, ram, software };
  }, [metrics.person_count, errorLogs.length]);

  const selectedSource = backendSources.find((item) => item.camera_id === selectedSourceId);

  useEffect(() => {
    if (sourceMode === "camera") {
      if (selectedSource) {
        setSourceHint(`Backend will open ${selectedSource.label} at ${selectedSource.resolution}.`);
      } else {
        setSourceHint("Pick one of the cameras discovered by the Python backend.");
      }
      return;
    }
    if (sourceMode === "network") {
      setSourceHint("Use a browser-playable or RTSP CCTV URL so the backend can process the live stream.");
      return;
    }
    setSourceHint("Upload a video file and CrowdCtrl will process it through the backend model.");
  }, [selectedSource, sourceMode]);

  const sourcePayloadForSelection = () => {
    if (sourceMode === "network") {
      const url = window.prompt("Enter CCTV stream URL for backend processing.");
      if (!url) return null;
      return {
        camera_id: "frontend_cctv",
        label: "Connected CCTV",
        source_type: "rtsp",
        source: url,
        enabled: true,
        area: { name: "CCTV Zone", fallback_area_sq_meters: 140.0, safe_density_per_sq_meter: 2.2 },
      };
    }
    if (!selectedSource) return null;
    return {
      camera_id: selectedSource.camera_id,
      label: selectedSource.label,
      source_type: selectedSource.source_type,
      source: selectedSource.source,
      enabled: true,
      area: {
        name: selectedSource.label,
        fallback_area_sq_meters: sourceMode === "camera" ? 80.0 : 70.0,
        safe_density_per_sq_meter: 2.5,
      },
    };
  };

  const startSource = async () => {
    try {
      if (sourceMode === "upload") {
        uploadRef.current?.click();
        return;
      }
      const payload = sourcePayloadForSelection();
      if (!payload) return;
      await apiJson("/control/start", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setActiveSourceLabel(payload.label);
      setRawFeedStatus("Backend raw feed live");
      setAnalysisFeedStatus("Backend model live");
      setRawFrameReady(false);
      setAnalysisFrameReady(false);
    } catch {
      setAnalysisFeedStatus("Start failed");
    }
  };

  const stopSource = () => {
    fetch(`${API_BASE}/control/stop`, { method: "POST" }).catch(() => {});
    setRawFeedStatus("Idle");
    setAnalysisFeedStatus("Waiting");
    setActiveSourceLabel("Not started");
    setRawFrameReady(false);
    setAnalysisFrameReady(false);
  };

  const onUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/control/upload`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload to backend failed.");
      setActiveSourceLabel(file.name);
      setRawFeedStatus("Uploaded footage");
      setAnalysisFeedStatus("Backend model live");
      setRawFrameReady(false);
      setAnalysisFrameReady(false);
    } catch {
      setAnalysisFeedStatus("Upload failed");
    }
  };

  const approveViewer = async (email) => {
    try {
      await apiJson("/auth/approve-viewer", {
        method: "POST",
        body: JSON.stringify({
          email,
          admin_email: session.email,
        }),
      });
      setPendingUsers((prev) => prev.filter((item) => item.email !== email));
    } catch {
      // ignore
    }
  };

  return (
    <div className="react-shell">
      <aside className="react-sidebar">
        <div className="brand-cluster">
          <div className={`brand-badge ${session.role === "admin" ? "admin" : ""}`}>CG</div>
          <div>
            <div className="brand-name">CrowdCtrl</div>
            <div className="brand-tag">{session.role === "admin" ? "Administrator console" : "Crowd risk monitoring"}</div>
          </div>
        </div>

        <nav className="react-nav">
          {["overview", "trends", "history"].map((key) => (
            <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
              {key === "overview" ? "Overview" : key === "trends" ? "Trends & Charts" : "History"}
            </button>
          ))}
          {session.role === "admin" ? (
            <button className={tab === "system" ? "active" : ""} onClick={() => setTab("system")}>System Health</button>
          ) : null}
        </nav>

        <div className="session-card">
          <div className="avatar-circle">{session.name.slice(0, 1).toUpperCase()}</div>
          <div>
            <div className="session-user">{session.name}</div>
            <div className="session-role">{session.email}</div>
          </div>
        </div>
        <button className="secondary" onClick={onLogout}>Log out</button>
      </aside>

      <main className="react-main">
        <header className="hero-top">
          <div>
            <p className="eyebrow">{session.role === "admin" ? "CrowdCtrl Admin" : "CrowdCtrl Control"}</p>
            <h1>{session.role === "admin" ? "Admin monitoring, approvals & system health" : "Dual-feed monitoring dashboard"}</h1>
          </div>
          <div className="hero-status">
            <span className={`pill ${apiOnline ? "online" : ""}`}>{apiOnline ? "API online" : "API offline"}</span>
            <span className="pill">{session.role === "admin" ? "Admin" : "Viewer"}</span>
          </div>
        </header>

        <section className="metric-grid">
          <Metric label="Current Count" value={metrics.person_count} />
          <Metric label="Safe Capacity" value={metrics.safe_capacity} />
          <Metric label="Area (sqm)" value={metrics.area_sq_meters} />
          <Metric label="Density (p/m^2)" value={metrics.density.toFixed(2)} />
        </section>

        <div className={`banner ${metrics.status === "CRITICAL" ? "critical" : metrics.status === "WARNING" ? "warning" : "neutral"}`}>
          {metrics.message}
        </div>

        {tab === "overview" ? (
          <>
            <section className="source-bar">
              <div className="field compact">
                <label>Source Type</label>
                <select value={sourceMode} onChange={(event) => setSourceMode(event.target.value)}>
                  <option value="camera">Backend Camera</option>
                  <option value="network">Connected CCTV</option>
                  <option value="upload">Upload Footage</option>
                </select>
              </div>
              <div className="field compact">
                <label>Backend Source</label>
                <select value={selectedSourceId} onChange={(event) => setSelectedSourceId(event.target.value)} disabled={sourceMode !== "camera"}>
                  {backendSources.filter((item) => item.kind === "camera").map((source) => (
                    <option key={source.camera_id} value={source.camera_id}>
                      {source.label} ({source.resolution})
                    </option>
                  ))}
                </select>
              </div>
              <div className="source-summary">
                <span className="source-summary-label">Backend routing</span>
                <strong>{sourceMode === "camera" ? (selectedSource?.label || "No camera selected") : sourceMode === "network" ? "Connected CCTV" : "Uploaded footage"}</strong>
                <span>{sourceHint}</span>
              </div>
              <input ref={uploadRef} type="file" accept="video/*" hidden onChange={onUpload} />
              <button className="primary" onClick={startSource}>Start / Select Source</button>
              <button className="secondary" onClick={stopSource}>Stop Feed</button>
            </section>

            <section className="feed-row">
              <article className="frame-card">
                <div className="frame-head">
                  <div>
                    <p className="eyebrow">Status Feed</p>
                    <h2>Raw hardware feed</h2>
                  </div>
                  <span className="pill">{rawFeedStatus}</span>
                </div>
                <div className="frame-box">
                  <img
                    ref={rawImageRef}
                    alt="Raw backend feed"
                    onLoad={() => setRawFrameReady(true)}
                    onError={() => {
                      setRawFrameReady(false);
                      setRawFeedStatus("No backend frame yet");
                    }}
                  />
                  {!rawFrameReady ? (
                    <div className="feed-placeholder">
                      <strong>{rawFeedStatus}</strong>
                      <span>Raw source comes directly from the backend capture pipeline.</span>
                    </div>
                  ) : null}
                </div>
              </article>

              <article className="frame-card">
                <div className="frame-head">
                  <div>
                    <p className="eyebrow">Analysis Feed</p>
                    <h2>Model overlay</h2>
                  </div>
                  <span className={`pill ${apiOnline ? "online" : ""}`}>{analysisFeedStatus}</span>
                </div>
                <div className="frame-box">
                  <img
                    ref={analysisImageRef}
                    alt="Model overlay"
                    onLoad={() => setAnalysisFrameReady(true)}
                    onError={() => {
                      setAnalysisFrameReady(false);
                      setAnalysisFeedStatus("Waiting for model output");
                    }}
                  />
                  {!analysisFrameReady ? (
                    <div className="feed-placeholder">
                      <strong>{analysisFeedStatus}</strong>
                      <span>Analysis feed mirrors the live CrowdCtrl YOLO output from the backend.</span>
                    </div>
                  ) : null}
                  {!apiOnline ? <p className="overlay-warning">Run <code>api.py</code> and start a source to see real YOLO annotations.</p> : null}
                  <p className="frame-note">This panel uses real annotated backend frames from CrowdCtrl.</p>
                </div>
              </article>
            </section>

            <section className="detail-panels">
              <InfoPanel title="Source summary" rows={[
                ["Active source", activeSourceLabel],
                ["Feed mode", sourceMode.toUpperCase()],
                ["Occupancy", `${Math.round(metrics.occupancy_ratio * 100)}%`],
                ["Last update", timeText(metrics.timestamp)],
              ]} />
              <InfoPanel title="Live counters" rows={[
                ["In Count", metrics.in_count],
                ["Out Count", metrics.out_count],
                ["Status", metrics.status],
                ["Message", metrics.message],
              ]} />
            </section>
          </>
        ) : null}

        {tab === "trends" ? (
          <section className="chart-row">
            <ChartCard title="Count over time" values={chartPoints.map((point) => point.count)} />
            <ChartCard title="Density trend" values={chartPoints.map((point) => point.density)} />
          </section>
        ) : null}

        {tab === "history" ? (
          <section className="history-row">
            <LogTable
              title="Alert Logs"
              rows={alertLogs.map((entry) => [entry.timestamp || entry.created_at, entry.severity, entry.person_count, entry.message])}
              headers={["Time", "Severity", "Count", "Message"]}
            />
            {session.role === "admin" ? (
              <LogTable
                title="30-Minute Crowd Snapshots"
                rows={metricSnapshots.map((entry) => [entry.timestamp || entry.created_at, entry.person_count, entry.density, entry.error_count])}
                headers={["Time", "People", "Density", "Errors"]}
              />
            ) : null}
          </section>
        ) : null}

        {tab === "system" && session.role === "admin" ? (
          <>
            <section className="metric-grid">
              <Metric label="CPU Utilization" value={summary.cpu} />
              <Metric label="RAM Utilization" value={summary.ram} />
              <Metric label="Software Health" value={summary.software} />
              <Metric label="Pending Users" value={pendingUsers.length} />
            </section>
            <section className="history-row">
              <ApprovalTable items={pendingUsers} onApprove={approveViewer} />
              <LogTable
                title="Forgot Password Requests"
                rows={passwordResetLogs.map((entry) => [entry.created_at, entry.email, entry.status, entry.message])}
                headers={["Time", "Email", "Status", "Message"]}
              />
            </section>
            <LogTable
              title="Error Log"
              rows={errorLogs.map((entry) => [entry.timestamp || entry.created_at, entry.camera_id, entry.stage, entry.message])}
              headers={["Time", "Camera", "Stage", "Message"]}
            />
          </>
        ) : null}
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function InfoPanel({ title, rows }) {
  return (
    <article className="card">
      <h3>{title}</h3>
      <ul className="detail-grid">
        {rows.map(([label, value]) => (
          <li key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </li>
        ))}
      </ul>
    </article>
  );
}

function LogTable({ title, headers, rows }) {
  return (
    <article className="card">
      <h3>{title}</h3>
      <div className="table-shell">
        <table>
          <thead>
            <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row, index) => (
              <tr key={`${title}-${index}`}>{row.map((cell, cellIndex) => <td key={`${title}-${index}-${cellIndex}`}>{cell}</td>)}</tr>
            )) : <tr><td colSpan={headers.length}>No data yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function ApprovalTable({ items, onApprove }) {
  return (
    <article className="card">
      <h3>Pending Viewer Approvals</h3>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Requested</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length ? items.map((item) => (
              <tr key={item.email}>
                <td>{item.name}</td>
                <td>{item.email}</td>
                <td>{item.created_at}</td>
                <td><button className="secondary small" onClick={() => onApprove(item.email)}>Approve</button></td>
              </tr>
            )) : <tr><td colSpan={4}>No pending viewers.</td></tr>}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function ChartCard({ title, values }) {
  const max = Math.max(...values, 1);
  return (
    <article className="card">
      <h3>{title}</h3>
      <div className="sparkline">
        {values.length ? values.map((value, index) => (
          <div key={`${title}-${index}`} className="bar" style={{ height: `${Math.max((Number(value) / max) * 100, 8)}%` }} />
        )) : <div className="empty-state">Waiting for live data.</div>}
      </div>
    </article>
  );
}

export default App;
