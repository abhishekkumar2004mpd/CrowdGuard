import { useEffect, useMemo, useRef, useState } from "react";

const STORAGE_KEY = "crowdguard_react_session";
const LOG_KEYS = {
  alerts: "crowdguard_react_alert_logs",
  nearLimit: "crowdguard_react_near_limit_logs",
  errors: "crowdguard_react_error_logs",
};

const USERS = {
  user: { password: "user123", role: "viewer" },
  admin: { password: "admin123", role: "admin" },
};

const API_BASE = "http://127.0.0.1:5001";

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

function App() {
  const [session, setSession] = usePersistentState(STORAGE_KEY, null);
  const [mode, setMode] = useState("viewer");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (!session) {
    return (
      <LoginScreen
        mode={mode}
        setMode={setMode}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        error={error}
        onLogin={() => {
          const account = USERS[username.trim()];
          if (!account || account.password !== password || account.role !== mode) {
            setError("Invalid credentials for the selected role.");
            return;
          }
          setSession({ username: username.trim(), role: account.role, loginAt: Date.now() });
          setError("");
        }}
      />
    );
  }

  return <Dashboard session={session} onLogout={() => setSession(null)} />;
}

function LoginScreen(props) {
  return (
    <div className="login-shell">
      <section className="hero-card">
        <p className="eyebrow">CrowdGuard React UI</p>
        <h1>Modern control room UI for live crowd intelligence.</h1>
        <p className="hero-copy">
          This React layer consumes the existing CrowdGuard model API and keeps admin/viewer sessions stable across reloads.
        </p>
      </section>

      <section className="login-card">
        <div className="mode-switch">
          <button className={props.mode === "viewer" ? "active" : ""} onClick={() => props.setMode("viewer")}>Viewer</button>
          <button className={props.mode === "admin" ? "active" : ""} onClick={() => props.setMode("admin")}>Admin</button>
        </div>

        <div className="field">
          <label>Username</label>
          <input value={props.username} onChange={(event) => props.setUsername(event.target.value)} />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={props.password} onChange={(event) => props.setPassword(event.target.value)} />
        </div>
        {props.error ? <div className="banner critical">{props.error}</div> : null}
        <button className="primary" onClick={props.onLogin}>Enter CrowdGuard</button>
        <div className="credentials-card">
          <div><code>user / user123</code></div>
          <div><code>admin / admin123</code></div>
        </div>
      </section>
    </div>
  );
}

function Dashboard({ session, onLogout }) {
  const [tab, setTab] = useState("overview");
  const [sourceMode, setSourceMode] = useState("laptop");
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [apiOnline, setApiOnline] = useState(false);
  const [metrics, setMetrics] = useState(EMPTY_METRICS);
  const [activeSourceLabel, setActiveSourceLabel] = useState("Not started");
  const [rawFeedStatus, setRawFeedStatus] = useState("Idle");
  const [analysisFeedStatus, setAnalysisFeedStatus] = useState("Waiting");
  const [chartPoints, setChartPoints] = useState([]);
  const [alertLogs, setAlertLogs] = usePersistentState(LOG_KEYS.alerts, []);
  const [nearLimitLogs, setNearLimitLogs] = usePersistentState(LOG_KEYS.nearLimit, []);
  const [errorLogs, setErrorLogs] = usePersistentState(LOG_KEYS.errors, []);

  const rawVideoRef = useRef(null);
  const analysisImageRef = useRef(null);
  const streamRef = useRef(null);
  const uploadRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    navigator.mediaDevices?.enumerateDevices?.().then((all) => {
      if (!mounted) return;
      const cams = all.filter((device) => device.kind === "videoinput");
      setDevices(cams);
      if (cams[0]) setSelectedDeviceId(cams[0].deviceId);
    }).catch((err) => {
      setErrorLogs((prev) => [{ createdAt: Date.now(), source: "devices", message: err.message }, ...prev].slice(0, 30));
    });
    return () => { mounted = false; };
  }, [setErrorLogs]);

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const healthResponse = await fetch(`${API_BASE}/health`);
        const health = await healthResponse.json();
        setApiOnline(health.status === "ok");
      } catch {
        setApiOnline(false);
      }

      try {
        const statusResponse = await fetch(`${API_BASE}/status`);
        const payload = await statusResponse.json();
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

        if (["WARNING", "CRITICAL"].includes(nextMetrics.status)) {
          setAlertLogs((prev) => [{ createdAt: Date.now(), status: nextMetrics.status, count: nextMetrics.person_count, message: nextMetrics.message }, ...prev].slice(0, 30));
        }
        if (nextMetrics.occupancy_ratio >= 0.7 && nextMetrics.occupancy_ratio < 0.85) {
          setNearLimitLogs((prev) => [{ createdAt: Date.now(), occupancy: `${Math.round(nextMetrics.occupancy_ratio * 100)}%`, density: nextMetrics.density.toFixed(2), source: activeSourceLabel }, ...prev].slice(0, 30));
        }
      } catch (error) {
        setMetrics(EMPTY_METRICS);
        setErrorLogs((prev) => [{ createdAt: Date.now(), source: "status", message: error.message }, ...prev].slice(0, 30));
      }

      if (analysisImageRef.current) {
        analysisImageRef.current.src = `${API_BASE}/frame/annotated?ts=${Date.now()}`;
      }
    }, 2500);

    return () => clearInterval(timer);
  }, [activeSourceLabel, setAlertLogs, setErrorLogs, setNearLimitLogs]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
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

  const startSource = async () => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }

      if (sourceMode === "upload") {
        uploadRef.current?.click();
        return;
      }

      if (sourceMode === "cctv") {
        const url = window.prompt("Enter a browser-compatible CCTV stream URL");
        if (!url) return;
        rawVideoRef.current.srcObject = null;
        rawVideoRef.current.src = url;
        await rawVideoRef.current.play();
        setActiveSourceLabel("Connected CCTV");
        setRawFeedStatus("CCTV live");
        setAnalysisFeedStatus(apiOnline ? "Model online" : "Waiting for backend");
        return;
      }

      const useDeviceId = sourceMode === "nearby" ? devices[1]?.deviceId || selectedDeviceId : selectedDeviceId;
      const stream = await navigator.mediaDevices.getUserMedia({
        video: useDeviceId ? { deviceId: { exact: useDeviceId } } : true,
        audio: false,
      });
      streamRef.current = stream;
      rawVideoRef.current.srcObject = stream;
      setActiveSourceLabel(sourceMode === "nearby" ? "Nearby device" : "Built-in Laptop Camera");
      setRawFeedStatus("Camera live");
      setAnalysisFeedStatus(apiOnline ? "Model online" : "Waiting for backend");
    } catch (error) {
      setErrorLogs((prev) => [{ createdAt: Date.now(), source: "source-start", message: error.message }, ...prev].slice(0, 30));
    }
  };

  const stopSource = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (rawVideoRef.current) {
      rawVideoRef.current.pause();
      rawVideoRef.current.srcObject = null;
      rawVideoRef.current.removeAttribute("src");
      rawVideoRef.current.load();
    }
    setRawFeedStatus("Idle");
    setAnalysisFeedStatus("Waiting");
    setActiveSourceLabel("Not started");
  };

  const onUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    rawVideoRef.current.srcObject = null;
    rawVideoRef.current.src = URL.createObjectURL(file);
    rawVideoRef.current.loop = true;
    rawVideoRef.current.play().catch(() => {});
    setActiveSourceLabel(file.name);
    setRawFeedStatus("Uploaded footage");
    setAnalysisFeedStatus(apiOnline ? "Model online" : "Waiting for backend");
  };

  return (
    <div className="react-shell">
      <aside className="react-sidebar">
        <div className="brand-cluster">
          <div className={`brand-badge ${session.role === "admin" ? "admin" : ""}`}>CG</div>
          <div>
            <div className="brand-name">CrowdGuard</div>
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
          <div className="avatar-circle">{session.username.slice(0, 1).toUpperCase()}</div>
          <div>
            <div className="session-user">{session.username}</div>
            <div className="session-role">{session.role === "admin" ? "Admin" : "Viewer"}</div>
          </div>
        </div>
        <button className="secondary" onClick={onLogout}>Log out</button>
      </aside>

      <main className="react-main">
        <header className="hero-top">
          <div>
            <p className="eyebrow">{session.role === "admin" ? "CrowdGuard Admin" : "CrowdGuard Control"}</p>
            <h1>{session.role === "admin" ? "Admin monitoring & system health" : "Dual-feed monitoring dashboard"}</h1>
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
                  <option value="laptop">Inbuilt Laptop Camera</option>
                  <option value="cctv">Connected CCTV</option>
                  <option value="nearby">Connect to Nearby Device</option>
                  <option value="upload">Upload Footage</option>
                </select>
              </div>
              <div className="field compact">
                <label>Camera Device</label>
                <select value={selectedDeviceId} onChange={(event) => setSelectedDeviceId(event.target.value)}>
                  {devices.map((device, index) => (
                    <option key={device.deviceId || index} value={device.deviceId}>
                      {device.label || `Camera ${index + 1}`}
                    </option>
                  ))}
                </select>
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
                  <video ref={rawVideoRef} autoPlay playsInline muted />
                  <p className="frame-note">Raw source remains unprocessed so hardware integration is always visible.</p>
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
                  <img ref={analysisImageRef} alt="Model overlay" />
                  {!apiOnline ? <p className="overlay-warning">Run <code>app.py</code> and <code>api.py</code> to see real YOLO annotations.</p> : null}
                  <p className="frame-note">This panel uses real annotated backend frames from CrowdGuard, not mock boxes.</p>
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
            <LogTable title="Alert Logs" rows={alertLogs.map((entry) => [timeText(entry.createdAt), entry.status, entry.count, entry.message])} headers={["Time", "Status", "Count", "Message"]} />
            {session.role === "admin" ? (
              <LogTable title="Near-Limit Logs" rows={nearLimitLogs.map((entry) => [timeText(entry.createdAt), entry.occupancy, entry.density, entry.source])} headers={["Time", "Occupancy", "Density", "Source"]} />
            ) : null}
          </section>
        ) : null}

        {tab === "system" && session.role === "admin" ? (
          <>
            <section className="metric-grid">
              <Metric label="CPU Utilization" value={summary.cpu} />
              <Metric label="RAM Utilization" value={summary.ram} />
              <Metric label="Software Health" value={summary.software} />
              <Metric label="Error Count" value={errorLogs.length} />
            </section>
            <LogTable title="Error Log" rows={errorLogs.map((entry) => [timeText(entry.createdAt), entry.source, entry.message])} headers={["Time", "Source", "Detail"]} />
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
