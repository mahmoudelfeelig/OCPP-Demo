"use client";

import { useEffect, useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";

type Item = Record<string, any>;

type DashboardState = {
  sites: Item[];
  stations: Item[];
  sessions: Item[];
  transactions: Item[];
  events: Item[];
  messages: Item[];
  outbox: Item[];
  webhooks: Item[];
  users: Item[];
  simulatorState: Item | null;
  scenarios: string[];
  systemStatus: Item | null;
};

type UserState = {
  email: string;
  role: "admin" | "operator";
};

type ConnectorItem = {
  id: string;
  station_id: string;
  connector_number: number;
  state: string;
  error_code?: string | null;
};

type DetailItem = {
  item: Item | null;
};

type SimulatorMessage = {
  timestamp?: string;
  direction?: string;
  payload?: unknown;
};

type PendingConfirmation = {
  path: string;
  label: string;
  message: string;
  body?: unknown;
} | null;

type DashboardView = "overview" | "sites" | "activity" | "simulator" | "sessions" | "admin";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const navItems = [
  { label: "Overview", id: "overview" },
  { label: "Sites", id: "sites" },
  { label: "Activity", id: "activity" },
  { label: "Simulator", id: "simulator" },
  { label: "Sessions", id: "sessions" },
  { label: "Admin & system", id: "admin" },
] as const;

const predefinedScenarios = [
  "happy-path-charging-session",
  "duplicate-meter-value",
  "station-offline-online",
  "connector-fault",
  "interrupted-session",
  "partner-webhook",
  "invalid-partner-signature",
  "duplicate-partner-event",
];

const initialState: DashboardState = {
  sites: [],
  stations: [],
  sessions: [],
  transactions: [],
  events: [],
  messages: [],
  outbox: [],
  webhooks: [],
  users: [],
  simulatorState: null,
  scenarios: predefinedScenarios,
  systemStatus: null,
};

const siteUrl = "https://elfeel.me";
const repoUrl = "https://github.com/mahmoudelfeelig/OCCP-Demo";

async function requestJson(path: string, init: RequestInit = {}, token?: string) {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, {
    ...init,
    headers,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new ApiError(data?.detail ?? data?.message ?? response.statusText, response.status);
  }
  return data;
}

function formatTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function Surface({
  tone = "light",
  className = "",
  children,
  ...props
}: {
  tone?: "light" | "dark";
  className?: string;
  children: ReactNode;
} & ComponentPropsWithoutRef<"section">) {
  return <section className={`surface ${tone === "light" ? "surface-light" : "surface-dark"} ${className}`} {...props}>{children}</section>;
}

function Metric({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string;
  subtext?: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {subtext ? <small>{subtext}</small> : null}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

function ElephantLogo({ className = "" }: { className?: string }) {
  return (
    <img className={`elephant-logo ${className}`} src="/assets/brand/elephant-logo.png" alt="Mahmoud Elfeel elephant logo" />
  );
}

function BrandLink({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-link ${compact ? "compact" : ""}`}>
      <button type="button" className="logo-refresh" onClick={() => window.location.reload()} aria-label="Refresh page">
        <ElephantLogo />
      </button>
      {!compact ? <span>QWELLO</span> : null}
    </div>
  );
}

function SiteLogoButton({ className = "" }: { className?: string }) {
  return (
    <button type="button" className={className} onClick={() => window.location.reload()} aria-label="Refresh page">
      <ElephantLogo />
    </button>
  );
}

function GitHubIcon() {
  return (
    <svg className="github-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 .7C5.7.7.8 5.6.8 11.9c0 4.9 3.2 9.1 7.7 10.6.6.1.8-.2.8-.5v-2c-3.1.7-3.8-1.3-3.8-1.3-.5-1.2-1.2-1.6-1.2-1.6-1-.7.1-.7.1-.7 1.1.1 1.7 1.1 1.7 1.1 1 .1.6 2.6 4.1 1.9.1-.7.4-1.2.7-1.5-2.5-.3-5.1-1.2-5.1-5.5 0-1.2.4-2.2 1.1-3-.1-.3-.5-1.5.1-2.9 0 0 .9-.3 3 1.1.9-.2 1.8-.4 2.7-.4s1.8.1 2.7.4c2.1-1.4 3-1.1 3-1.1.6 1.4.2 2.6.1 2.9.7.8 1.1 1.8 1.1 3 0 4.3-2.6 5.2-5.1 5.5.4.3.8 1 .8 2.1v3c0 .3.2.6.8.5 4.5-1.5 7.7-5.7 7.7-10.6C23.2 5.6 18.3.7 12 .7Z"
      />
    </svg>
  );
}

function AppFooter() {
  return (
    <footer className="app-footer">
      <SiteLogoButton className="footer-logo" />
      <span>© Mahmoud elfeel 2026</span>
      <a className="footer-github" href={repoUrl} aria-label="Open GitHub repository">
        <GitHubIcon />
      </a>
    </footer>
  );
}

function ConfirmDialog({
  pending,
  busy,
  onCancel,
  onConfirm,
}: {
  pending: PendingConfirmation;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  if (!pending) return null;

  return (
    <div className="confirm-layer" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onCancel();
    }}>
      <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div>
          <span className="confirm-kicker">Confirm action</span>
          <h2 id="confirm-title">{pending.label}</h2>
          <p>{pending.message}</p>
        </div>
        <div className="confirm-actions">
          <button type="button" className="ghost-button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="primary-button" onClick={onConfirm} disabled={busy}>
            {busy ? "Working..." : "Continue"}
          </button>
        </div>
      </section>
    </div>
  );
}

function LoginScreen({
  onSubmit,
  loading,
  error,
}: {
  onSubmit: (email: string, password: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <main className="login-screen">
      <aside className="login-rail">
        <BrandLink />
        <div className="rail-copy">
          <p>EV charging backend lifecycle demo.</p>
        </div>
      </aside>

      <section className="login-card">
        <div className="login-card-top">
          <div className="eyebrow">overview</div>
          <h1>Fleet at a glance</h1>
          <p>Sign in to inspect stations, sessions, messages, webhooks, and recovery controls.</p>
        </div>
        <form
          className="login-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSubmit(email, password);
          }}
        >
          <label>
            Email
            <input value={email} placeholder="Email" onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} placeholder="Password" onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
          {error ? <p className="error">{error}</p> : null}
        </form>
      </section>
      <AppFooter />
    </main>
  );
}

export default function Page() {
  const [loading, setLoading] = useState(true);
  const [loginLoading, setLoginLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserState | null>(null);
  const [state, setState] = useState<DashboardState>(initialState);
  const [health, setHealth] = useState<{ status?: string; worker?: string; cache?: string }>({});
  const [ready, setReady] = useState<{ status?: string }>({});
  const [actionLabel, setActionLabel] = useState("Ready");
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [selectedStationId, setSelectedStationId] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedConnectorId, setSelectedConnectorId] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState("happy-path-charging-session");
  const [scenarioSpeed, setScenarioSpeed] = useState("normal");
  const [stationDetail, setStationDetail] = useState<DetailItem>({ item: null });
  const [sessionDetail, setSessionDetail] = useState<DetailItem>({ item: null });
  const [transactionDetail, setTransactionDetail] = useState<DetailItem>({ item: null });
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);
  const [newUser, setNewUser] = useState({ email: "", password: "", role: "operator", display_name: "" });
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [activeView, setActiveView] = useState<DashboardView>("overview");

  function clearSession(message = "Session expired. Sign in again.") {
    window.localStorage.removeItem("ocpp-token");
    setToken(null);
    setUser(null);
    setError(message);
  }

  async function loadDashboard(accessToken: string, role: "admin" | "operator") {
    const [
      sites,
      stations,
      sessions,
      transactions,
      events,
      messages,
      outbox,
      webhooks,
      users,
      healthInfo,
      readyInfo,
      statusInfo,
      scenariosInfo,
      simulatorInfo,
    ] = await Promise.all([
      requestJson("/api/sites", {}, accessToken),
      requestJson("/api/stations", {}, accessToken),
      requestJson("/api/sessions", {}, accessToken),
      requestJson("/api/transactions", {}, accessToken),
      requestJson("/api/events", {}, accessToken),
      requestJson("/api/messages", {}, accessToken),
      requestJson("/api/outbox", {}, accessToken),
      requestJson("/api/webhooks", {}, accessToken),
      role === "admin" ? requestJson("/api/admin/users", {}, accessToken) : Promise.resolve([]),
      requestJson("/api/health"),
      requestJson("/api/ready"),
      requestJson("/api/metrics/status"),
      requestJson("/simulator/scenarios"),
      requestJson("/simulator/state"),
    ]);

    setState({
      sites: sites.items ?? [],
      stations: stations.items ?? [],
      sessions: sessions.items ?? [],
      transactions: transactions.items ?? [],
      events: events.items ?? [],
      messages: messages.items ?? [],
      outbox: outbox.items ?? [],
      webhooks: webhooks.items ?? [],
      users: Array.isArray(users) ? users : [],
      scenarios: scenariosInfo.scenarios?.length ? scenariosInfo.scenarios : predefinedScenarios,
      simulatorState: simulatorInfo,
      systemStatus: statusInfo,
    });
    setHealth(healthInfo);
    setReady(readyInfo);
    setActionLabel(`Worker ${statusInfo.worker ?? "unknown"} · Cache ${statusInfo.cache ?? "unknown"}`);
    setActionError(null);
  }

  useEffect(() => {
    const storedToken = window.localStorage.getItem("ocpp-token");
    if (!storedToken) {
      setLoading(false);
      return;
    }

    setToken(storedToken);
    requestJson("/api/auth/me", {}, storedToken)
      .then(async (profile) => {
        setUser(profile);
        await loadDashboard(storedToken, profile.role);
      })
      .catch(() => {
        clearSession();
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!state.sites.length) return;
    if (!selectedSiteId) setSelectedSiteId(state.sites[0].id);
    if (!selectedStationId) setSelectedStationId(state.stations[0]?.id ?? null);
    if (!selectedSessionId) setSelectedSessionId(state.sessions[0]?.id ?? null);
  }, [state, selectedSiteId, selectedStationId, selectedSessionId]);

  const selectedSite = state.sites.find((site) => site.id === selectedSiteId) ?? state.sites[0];
  const selectedStation = state.stations.find((station) => station.id === selectedStationId) ?? state.stations[0];
  const selectedSession = state.sessions.find((session) => session.id === selectedSessionId) ?? state.sessions[0];
  const selectedConnector = connectors.find((connector) => connector.id === selectedConnectorId) ?? connectors[0];

  const siteStations = useMemo(
    () => state.stations.filter((station) => station.site_id === selectedSite?.id),
    [state.stations, selectedSite?.id],
  );
  const siteSessions = useMemo(
    () => state.sessions.filter((session) => session.site_id === selectedSite?.id),
    [state.sessions, selectedSite?.id],
  );
  const stationMessages = useMemo(
    () => state.messages.filter((message) => message.station_id === selectedStation?.id).slice(0, 6),
    [state.messages, selectedStation?.id],
  );
  const selectedTransaction = selectedSession?.transaction
    ? state.transactions.find((txn) => txn.id === selectedSession.transaction.id) ?? selectedSession.transaction
    : null;
  const liveEvents = state.events.slice(0, 12);
  const selectedStateHistory = state.events
    .filter((event) => {
      if (!selectedSession) return false;
      return [
        selectedSession.id,
        selectedSession.station_id,
        selectedSession.connector_id,
        selectedSession.transaction?.id,
      ].includes(event.entity_id);
    })
    .slice(0, 6);
  const outboxRows = state.outbox.slice(0, 8);
  const webhookRows = state.webhooks.slice(0, 8);
  const simulatorMessages = ((state.simulatorState?.messages as SimulatorMessage[] | undefined) ?? []).slice(-4);

  useEffect(() => {
    if (!token || !selectedStation?.id) return;
    requestJson(`/api/stations/${selectedStation.id}/connectors`, {}, token)
      .then((result) => {
        setConnectors(result.items ?? []);
        setSelectedConnectorId(result.items?.[0]?.id ?? null);
      })
      .catch(() => setConnectors([]));
    requestJson(`/api/stations/${selectedStation.id}`, {}, token)
      .then((result) => setStationDetail(result))
      .catch(() => setStationDetail({ item: null }));
  }, [selectedStation?.id, token]);

  useEffect(() => {
    if (!token || !selectedSession?.id) return;
    requestJson(`/api/sessions/${selectedSession.id}`, {}, token)
      .then((result) => setSessionDetail(result))
      .catch(() => setSessionDetail({ item: null }));
  }, [selectedSession?.id, token]);

  useEffect(() => {
    if (!token || !selectedTransaction?.id) return;
    requestJson(`/api/transactions/${selectedTransaction.id}`, {}, token)
      .then((result) => setTransactionDetail(result))
      .catch(() => setTransactionDetail({ item: null }));
  }, [selectedTransaction?.id, token]);

  if (loading) {
    return (
      <main className="loading-screen">
        <div className="loading-card">
          <div className="eyebrow">booting</div>
          <h1>Preparing operations console</h1>
          <p>Loading fleet state and auth.</p>
        </div>
      </main>
    );
  }

  if (!user || !token) {
    return (
      <LoginScreen
        loading={loginLoading}
        error={error}
        onSubmit={async (email, password) => {
          setLoginLoading(true);
          setError(null);
          try {
            const result = await requestJson("/api/auth/login", {
              method: "POST",
              body: JSON.stringify({ email, password }),
            });
            window.localStorage.setItem("ocpp-token", result.access_token);
            setToken(result.access_token);
            const profile = await requestJson("/api/auth/me", {}, result.access_token);
            setUser(profile);
            await loadDashboard(result.access_token, profile.role);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
          } finally {
            setLoginLoading(false);
          }
        }}
      />
    );
  }

  const isAdmin = user.role === "admin";
  const totalStations = state.stations.length;
  const onlineStations = state.stations.filter((station) => station.online).length;
  const activeSessions = state.sessions.filter((session) => session.state === "active").length;
  const outboxRetrying = state.outbox.filter((row) => row.status === "retrying").length;
  const webhookFailures = state.webhooks.filter((row) => row.status === "failed").length;
  const selectedOutboxId = outboxRows[0]?.id ?? null;

  async function refresh() {
    if (!token || !user) return;
    try {
      await loadDashboard(token, user.role);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) clearSession();
      else {
        const message = err instanceof Error ? err.message : "Refresh failed";
        setActionLabel(message);
        setActionError(message);
      }
    }
  }

  async function postAction(path: string, label: string, body?: unknown) {
    if (!token) {
      setActionLabel("Sign in required");
      return;
    }
    setActionLabel(label);
    setActionError(null);
    try {
      await requestJson(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      }, token);
      await refresh();
      setActionLabel(`${label} complete`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) clearSession();
      else {
        const message = err instanceof Error ? err.message : "Action failed";
        setActionLabel(message);
        setActionError(message);
      }
    }
  }

  async function confirmAndPost(path: string, label: string, message: string, body?: unknown) {
    setPendingConfirmation({ path, label, message, body });
  }

  async function acceptConfirmation() {
    if (!pendingConfirmation) return;
    setConfirmBusy(true);
    try {
      await postAction(pendingConfirmation.path, pendingConfirmation.label, pendingConfirmation.body);
      setPendingConfirmation(null);
    } finally {
      setConfirmBusy(false);
    }
  }

  async function runScenario() {
    const body = {
      site_id: selectedSite?.id ?? null,
      station_id: selectedStation?.id ?? null,
      connector_id: selectedConnector?.connector_number ? String(selectedConnector.connector_number) : null,
      speed: scenarioSpeed,
    };
    await postAction(`/simulator/run/${selectedScenario}`, `Running ${selectedScenario}`, body);
  }

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <div>
          <BrandLink />
          <div className="sidebar-copy">
            <p>Operations console</p>
            <p>Fleet operations dashboard.</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeView === item.id ? "active" : ""}
              onClick={() => setActiveView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <strong>{user.email}</strong>
            <span>{user.role.toUpperCase()}</span>
          </div>
          <button
            type="button"
            className="ghost-button"
            onClick={() => {
              window.localStorage.removeItem("ocpp-token");
              setToken(null);
              setUser(null);
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <button type="button" onClick={refresh}>
            Refresh
          </button>
        </header>

        <div className="view-content">
        {activeView === "overview" ? <div className="hero-row">
          <Surface tone="dark" className="overview-card" id="overview">
            <div className="card-head">
              <div>
                <div className="eyebrow">overview</div>
                <h1>Fleet at a glance</h1>
              </div>
              <div className="status-pills">
                <span>Environment</span>
                <strong>LOCAL</strong>
                <span>Health</span>
                <strong>{ready.status?.toUpperCase() ?? "GOOD"}</strong>
                <span>Time</span>
                <strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</strong>
              </div>
            </div>

            <div className="kpi-grid">
              <Metric label="Sites" value={`${state.sites.length}`} subtext={`${state.sites.filter((site) => site.is_active).length} active`} />
              <Metric label="Stations" value={`${totalStations}`} subtext={`${totalStations - onlineStations} offline`} />
              <Metric label="Connectors" value={`${state.stations.reduce((total, station) => total + (station.connector_count ?? 0), 0)}`} subtext={`${state.outbox.length} outbox`} />
              <Metric label="Active Sessions" value={`${activeSessions}`} subtext={`${webhookFailures} webhook failures`} />
            </div>

            <div className="mini-panels">
              <div className="mini-panel dark">
                <h3>Station status</h3>
                <p>Online {onlineStations}</p>
                <p>Offline {totalStations - onlineStations}</p>
                <p>Faulted {state.stations.filter((station) => station.state === "faulted").length}</p>
              </div>
              <div className="mini-panel dark">
                <h3>Outbox health</h3>
                <p>Processed {state.outbox.filter((row) => row.status === "processed").length}</p>
                <p>Retrying {outboxRetrying}</p>
                <p>Dead-lettered {state.outbox.filter((row) => row.status === "dead_lettered").length}</p>
                <p>Acknowledged {state.outbox.filter((row) => row.acknowledged_at).length}</p>
              </div>
              <div className="mini-panel dark">
                <h3>Webhooks</h3>
                <p>Received {state.webhooks.length}</p>
                <p>Valid {state.webhooks.filter((row) => row.signature_valid).length}</p>
                <p>Failures {webhookFailures}</p>
              </div>
            </div>
          </Surface>

          <Surface tone="dark" className="station-card" id="station-detail">
            <div className="station-detail-head">
              <div>
                <div className="breadcrumb">Stations / {selectedStation?.external_id ?? "—"}</div>
                <h2>{selectedStation?.label ?? "Select a station"}</h2>
                <div className="station-meta">
                  <span>Site {stationDetail.item?.site_id ?? selectedStation?.site_id ?? "—"}</span>
                  <span>Model UltraCharge 3000</span>
                  <span>Firmware 1.2.8</span>
                  <span>Last seen {stationDetail.item?.last_seen_at ? formatTime(stationDetail.item.last_seen_at) : selectedStation?.last_seen_at ? formatTime(selectedStation.last_seen_at) : "—"}</span>
                </div>
              </div>
              <div className="station-actions-top">
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost(`/api/admin/stations/${selectedStation.id}/maintenance`, "Toggle maintenance", "Toggle station maintenance mode? This changes live station behavior.", { enabled: !selectedStation.maintenance_mode })}>
                  Maintenance
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost(`/api/admin/stations/${selectedStation.id}/maintenance`, "Toggle maintenance", "Open station actions and maintenance controls?", { enabled: !selectedStation.maintenance_mode })}>
                  More
                </button>
              </div>
            </div>

            <div className="station-layout">
              <div className="station-render">
                <div className="charger-mock">
                  <div className="charger-screen">300</div>
                  <div className="charger-body" />
                </div>
              </div>

              <div className="connector-table">
                <div className="table-head">
                  <span>Connector</span>
                  <span>Status</span>
                  <span>Session</span>
                  <span>Power</span>
                  <span>Last Update</span>
                </div>
              {connectors.map((connector) => (
                  <button
                    key={connector.id}
                    type="button"
                    className={`connector-row ${selectedConnector?.id === connector.id ? "selected" : ""}`}
                    onClick={() => setSelectedConnectorId(connector.id)}
                  >
                    <span className="connector-number">{String(connector.connector_number).padStart(2, "0")}</span>
                    <span className={`status-pill ${connector.state}`}>{connector.state.toUpperCase()}</span>
                    <span>{selectedSession?.external_session_id ?? "—"}</span>
                    <span>{connector.state === "charging" ? "32.4 kW" : "0 kW"}</span>
                    <span>{formatTime(selectedStation?.last_seen_at)}</span>
                  </button>
                ))}
                {!connectors.length ? <EmptyState label="No connectors reported for this station." /> : null}
              </div>
            </div>

            <div className="station-bottom">
              <div className="recent-messages">
                <h3>Recent messages</h3>
                {stationMessages.map((message) => (
                  <div key={message.id} className="message-line">
                    <span>{formatTime(message.received_at)}</span>
                    <strong>{message.action}</strong>
                    <small>id: {message.message_id}</small>
                  </div>
                ))}
                {!stationMessages.length ? <EmptyState label="No station messages yet." /> : null}
                <button type="button" className="text-link" onClick={() => setActiveView("activity")}>
                  View all messages →
                </button>
              </div>

              <div className="station-actions">
                <h3>Actions</h3>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost(`/api/admin/stations/${selectedStation.id}/maintenance`, "Enable maintenance", "Enable station maintenance mode?", { enabled: true })}>
                  Station maintenance mode
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost(`/api/admin/connectors/${selectedConnector?.id ?? ""}/available`, "Connector available", "Mark connector available?")}>
                  Mark available
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost(`/api/admin/connectors/${selectedConnector?.id ?? ""}/unavailable`, "Connector unavailable", "Mark connector unavailable?")}>
                  Mark unavailable
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost("/api/admin/simulator/remote-start", "Remote start transaction", "Trigger a remote start simulation?")}>
                  Remote start transaction
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedStation && confirmAndPost("/api/admin/simulator/remote-stop", "Remote stop transaction", "Trigger a remote stop simulation?")}>
                  Remote stop transaction
                </button>
                <button type="button" className="ghost-button" onClick={() => selectedOutboxId && confirmAndPost(`/api/admin/outbox/${selectedOutboxId}/retry`, "Retry outbox", "Retry the selected outbox event?")}>
                  View audit log
                </button>
              </div>
            </div>

            <div className="connector-drawer">
              <div className="drawer-head">
                <span>Connector detail</span>
                <strong>{selectedConnector ? `#${selectedConnector.connector_number}` : "None selected"}</strong>
              </div>
              <p>Status {selectedConnector?.state?.toUpperCase() ?? "—"}</p>
              <p>Fault {selectedConnector?.error_code ?? "None"}</p>
              <p>Station {selectedConnector?.station_id ?? "—"}</p>
            </div>
          </Surface>
        </div> : null}

        <div className={`lower-grid view-${activeView}`}>
          {activeView === "activity" ? <Surface tone="dark" className="stream-card" id="events">
            <div className="card-head">
              <div>
                <div className="eyebrow">event stream</div>
                <h2>Live events</h2>
              </div>
              <div className="card-subnav">
                <span>All</span>
                <span>OCPP</span>
                <span>Webhook</span>
                <span>Admin</span>
              </div>
            </div>
            <div className="timeline">
              {liveEvents.map((event) => (
                <div key={event.id} className="timeline-row">
                  <span className="timeline-time">{formatTime(event.created_at)}</span>
                  <span className="timeline-tag">{event.action}</span>
                  <span className="timeline-text">{event.entity_type} {event.entity_id}</span>
                </div>
              ))}
              {!liveEvents.length ? <EmptyState label="No events yet. Run a simulator scenario to populate the stream." /> : null}
            </div>
          </Surface> : null}

          {activeView === "sites" ? <Surface tone="dark" className="map-card" id="sites">
            <div className="card-head">
              <div>
                <div className="eyebrow">sites</div>
                <h2>Sites</h2>
              </div>
            </div>
            <div className="site-list">
              {state.sites.map((site) => {
                const stationsForSite = state.stations.filter((station) => station.site_id === site.id);
                const onlineForSite = stationsForSite.filter((station) => station.online).length;
                return (
                  <button
                    key={site.id}
                    type="button"
                    className={`site-row ${selectedSite?.id === site.id ? "selected" : ""}`}
                    onClick={() => {
                      setSelectedSiteId(site.id);
                      setSelectedStationId(stationsForSite[0]?.id ?? null);
                    }}
                  >
                    <span>
                      <strong>{site.label}</strong>
                      <small>{site.is_active ? "Active site" : "Inactive site"}</small>
                    </span>
                    <span>
                      <strong>{stationsForSite.length}</strong>
                      <small>{onlineForSite} online</small>
                    </span>
                  </button>
                );
              })}
              {!state.sites.length ? <EmptyState label="No sites seeded." /> : null}
            </div>
          </Surface> : null}

          {activeView === "simulator" ? <Surface tone="dark" className="simulator-card" id="simulator">
            <div className="card-head">
              <div>
                <div className="eyebrow">simulator</div>
                <h2>Scenarios</h2>
              </div>
            </div>
            <div className="user-form simulator-form">
              <select value={selectedSiteId ?? ""} onChange={(event) => setSelectedSiteId(event.target.value)}>
                {state.sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.label}
                  </option>
                ))}
              </select>
              <select value={selectedStationId ?? ""} onChange={(event) => setSelectedStationId(event.target.value)}>
                {siteStations.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.label}
                  </option>
                ))}
              </select>
              <select value={selectedConnectorId ?? ""} onChange={(event) => setSelectedConnectorId(event.target.value)}>
                {connectors.map((connector) => (
                  <option key={connector.id} value={connector.id}>
                    Connector {connector.connector_number}
                  </option>
                ))}
              </select>
              <select value={scenarioSpeed} onChange={(event) => setScenarioSpeed(event.target.value)}>
                <option value="slow">slow</option>
                <option value="normal">normal</option>
                <option value="fast">fast</option>
              </select>
            </div>
            <div className="scenario-list">
              {state.scenarios.map((scenario) => (
                <button key={scenario} type="button" className={`scenario-chip ${selectedScenario === scenario ? "selected" : ""}`} onClick={() => setSelectedScenario(scenario)}>
                  <strong>{scenario.replace(/-/g, " ")}</strong>
                  <span>Run {scenario.includes("duplicate") ? "duplicate" : "normal"} path</span>
                </button>
              ))}
            </div>
            <div className="simulator-preview">
              <button type="button" className="ghost-button" onClick={runScenario}>
                Run simulation
              </button>
              <button type="button" className="danger-button" onClick={() => postAction("/api/admin/simulator/remote-stop", "Stop simulation")}>
                Stop simulation
              </button>
            </div>
            <div className="simulator-preview">
              <div className="simulator-status">{state.simulatorState?.running ? "Simulation running..." : "Ready"}</div>
            </div>
            <div className="timeline simulator-timeline">
              {simulatorMessages.map((entry, index) => (
                <div key={`${entry.timestamp}-${index}`} className="timeline-row">
                  <span className="timeline-time">{formatTime(entry.timestamp)}</span>
                  <span className="timeline-tag">{entry.direction ?? "event"}</span>
                  <span className="timeline-text">{typeof entry.payload === "string" ? entry.payload : JSON.stringify(entry.payload)}</span>
                </div>
              ))}
              {!simulatorMessages.length ? <EmptyState label="No simulator messages yet." /> : null}
            </div>
          </Surface> : null}

          {activeView === "sessions" ? <Surface tone="dark" className="session-card" id="sessions">
            <div className="card-head">
              <div>
                <div className="eyebrow">session</div>
                <h2>{selectedSession?.external_session_id ?? "No session"}</h2>
              </div>
            </div>
            <div className="detail-pairs">
              <div><span>Status</span><strong>{sessionDetail.item?.state?.toUpperCase() ?? selectedSession?.state?.toUpperCase() ?? "—"}</strong></div>
              <div><span>Site</span><strong>{sessionDetail.item?.site_id ?? selectedSession?.site_id ?? "—"}</strong></div>
              <div><span>Station</span><strong>{sessionDetail.item?.station_id ?? selectedSession?.station_id ?? "—"}</strong></div>
              <div><span>Connector</span><strong>{sessionDetail.item?.connector_id ?? selectedSession?.connector_id ?? "—"}</strong></div>
              <div><span>Started</span><strong>{formatDateTime(sessionDetail.item?.started_at ?? selectedSession?.started_at)}</strong></div>
              <div><span>Duration</span><strong>{sessionDetail.item?.ended_at ? "00:34:21" : "running"}</strong></div>
            </div>
            <div className="transaction-box">
              <span>Transaction</span>
              <strong>{transactionDetail.item?.ocpp_transaction_id ?? selectedTransaction?.ocpp_transaction_id ?? "—"}</strong>
              <small>{transactionDetail.item?.state?.toUpperCase() ?? selectedTransaction?.state?.toUpperCase() ?? "OPEN"}</small>
            </div>
            <div className="meter-timeline">
              {(sessionDetail.item?.meter_values ?? []).map((entry: Item) => (
                <div key={entry.id} className="meter-row">
                  <span>{formatTime(entry.sampled_at)}</span>
                  <strong>{entry.value_kwh} {entry.unit}</strong>
                </div>
              ))}
              {!(sessionDetail.item?.meter_values ?? []).length ? <EmptyState label="No meter values recorded for this session." /> : null}
            </div>
            <div className="state-history">
              <h3>State history</h3>
              {selectedStateHistory.map((event) => (
                <div key={event.id} className="message-line">
                  <span>{formatTime(event.created_at)}</span>
                  <strong>{event.entity_type}</strong>
                  <small>{event.action}</small>
                </div>
              ))}
              {!selectedStateHistory.length ? <EmptyState label="No state transitions recorded for this selection." /> : null}
            </div>
            <button type="button" className="ghost-button wide">View full detail</button>
          </Surface> : null}

          {activeView === "activity" ? <Surface tone="dark" className="raw-card" id="messages">
            <div className="card-head">
              <div>
                <div className="eyebrow">raw message</div>
                <h2>Message payload</h2>
              </div>
            </div>
            <pre className="message-code">{JSON.stringify(state.messages[0]?.payload ?? { action: "BootNotification", payload: "…" }, null, 2)}</pre>
            <div className="raw-meta">
              <div>
                <span>Message ID</span>
                <strong>{state.messages[0]?.message_id ?? "—"}</strong>
              </div>
              <div>
                <span>Received</span>
                <strong>{formatTime(state.messages[0]?.received_at)}</strong>
              </div>
            </div>
          </Surface> : null}

          {activeView === "admin" ? <Surface tone="dark" className="admin-card" id="admin">
            <div className="card-head">
              <div>
                <div className="eyebrow">admin</div>
                <h2>Operations</h2>
              </div>
            </div>
            <div className="admin-actions">
              <button type="button" className="ghost-button" onClick={() => confirmAndPost("/api/admin/simulator/remote-start", "Remote start simulation", "Remote start the simulation?")}>
                Remote start simulation
              </button>
              <button type="button" className="ghost-button" onClick={() => confirmAndPost("/api/admin/simulator/remote-stop", "Remote stop simulation", "Remote stop the simulation?")}>
                Remote stop simulation
              </button>
              <button type="button" className="ghost-button" onClick={() => selectedOutboxId && confirmAndPost(`/api/admin/outbox/${selectedOutboxId}/retry`, "Retry failed outbox", "Retry the selected failed outbox event?")}>
                Retry failed outbox
              </button>
              <button type="button" className="ghost-button" onClick={() => selectedOutboxId && confirmAndPost(`/api/admin/outbox/${selectedOutboxId}/ack`, "Acknowledge dead letter", "Acknowledge the selected dead-letter event?")}>
                Acknowledge dead letter
              </button>
            </div>

            {isAdmin ? (
              <div className="user-admin">
                <h3>Users and roles</h3>
                <div className="user-table">
                  {state.users.map((item) => (
                    <div key={item.id} className="user-row">
                      <span>{item.email}</span>
                      <strong>{item.role}</strong>
                    </div>
                  ))}
                  {!state.users.length ? <EmptyState label="No users loaded." /> : null}
                </div>
                <div className="user-form">
                  <input placeholder="email" value={newUser.email} onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))} />
                  <input placeholder="password" type="password" value={newUser.password} onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))} />
                  <select value={newUser.role} onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value }))}>
                    <option value="operator">operator</option>
                    <option value="admin">admin</option>
                  </select>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => confirmAndPost("/api/admin/users", "Create user", "Create a new user with these credentials?", newUser)}
                  >
                    Create user
                  </button>
                  <button type="button" className="ghost-button user-form-wide" disabled title="Rotate the partner webhook secret by updating deploy/.env and restarting the stack.">
                    Rotate webhook secret
                  </button>
                </div>
              </div>
            ) : null}
          </Surface> : null}

          {activeView === "admin" || activeView === "activity" ? <Surface tone="dark" className="system-card" id="system">
            <div className="card-head">
              <div>
                <div className="eyebrow">system</div>
                <h2>Health and observability</h2>
              </div>
            </div>
            <div className="system-grid">
              <Metric label="API" value={health.status ?? "unknown"} />
              <Metric label="Worker" value={health.worker ?? "unknown"} />
              <Metric label="Cache" value={health.cache ?? "unknown"} />
              <Metric label="Outbox" value={`${state.outbox.length}`} />
            </div>
            <div className="system-summary">
              <div>
                <span>Connected stations</span>
                <strong>{state.systemStatus?.connected_stations ?? "—"}</strong>
              </div>
              <div>
                <span>Active sessions</span>
                <strong>{state.systemStatus?.active_sessions ?? "—"}</strong>
              </div>
              <div>
                <span>Processed messages</span>
                <strong>{state.systemStatus?.processed_messages ?? "—"}</strong>
              </div>
              <div>
                <span>Retry lag</span>
                <strong>{state.systemStatus?.worker_lag_seconds != null ? `${state.systemStatus.worker_lag_seconds}s` : "—"}</strong>
              </div>
            </div>
            <div className="webhook-feed">
              <h3>Webhooks</h3>
              {webhookRows.map((row) => (
                <div key={row.id} className="user-row">
                  <span>{row.event_id}</span>
                  <strong>{row.status}</strong>
                </div>
              ))}
              {!webhookRows.length ? <EmptyState label="No partner webhook events yet." /> : null}
            </div>
          </Surface> : null}
        </div>
        </div>
        <AppFooter />
      </section>
      <ConfirmDialog
        pending={pendingConfirmation}
        busy={confirmBusy}
        onCancel={() => setPendingConfirmation(null)}
        onConfirm={acceptConfirmation}
      />
    </main>
  );
}
