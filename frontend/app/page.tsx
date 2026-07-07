"use client";

import Image from "next/image";
import { useEffect, useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";

type JsonRecord = Record<string, unknown>;
type RoleName = "admin" | "operator";

type SiteItem = {
  id: string;
  slug?: string;
  label: string;
  is_active: boolean;
};

type StationItem = {
  id: string;
  site_id: string;
  external_id?: string;
  label: string;
  state?: string;
  online?: boolean;
  last_seen_at?: string | null;
  connector_count?: number;
  maintenance_mode?: boolean;
};

type SessionItem = {
  id: string;
  external_session_id?: string;
  site_id: string;
  station_id: string;
  connector_id?: string | null;
  state?: string;
  started_at?: string | null;
  ended_at?: string | null;
  transaction?: TransactionItem;
};

type TransactionItem = {
  id: string;
  ocpp_transaction_id?: string | number;
  state?: string;
};

type MeterValueItem = {
  id: string;
  sampled_at?: string | null;
  value_kwh?: string | number;
  unit?: string;
};

type StationDetailItem = StationItem & JsonRecord;
type SessionDetailItem = SessionItem & { meter_values?: MeterValueItem[] } & JsonRecord;
type TransactionDetailItem = TransactionItem & JsonRecord;

type EventItem = {
  id: string;
  action?: string;
  event_type?: string;
  entity_type?: string;
  entity_id?: string | null;
  created_at?: string | null;
};

type MessageItem = {
  id: string;
  station_id?: string | null;
  action?: string;
  message_id?: string | null;
  status?: string;
  received_at?: string | null;
  payload?: JsonRecord;
};

type OutboxItem = {
  id: string;
  status?: string;
  acknowledged_at?: string | null;
};

type WebhookItem = {
  id: string;
  event_id?: string;
  status?: string;
  signature_valid?: boolean;
};

type UserItem = {
  id: string;
  email: string;
  role: RoleName;
  display_name?: string | null;
  is_active: boolean;
  created_at?: string | null;
  last_login_at?: string | null;
};

type SystemStatus = {
  worker?: string;
  worker_detail?: string;
  cache?: string;
  cache_detail?: string;
  status?: string;
  connected_stations?: string;
  active_sessions?: string;
  processed_messages?: string;
  failed_messages?: string;
  retrying_outbox?: string;
  pending_outbox?: string;
  processing_outbox?: string;
  worker_lag_seconds?: string;
};

type HealthState = {
  status?: string;
  worker?: string;
  cache?: string;
};

type ReadyState = {
  status?: string;
};

type ListResponse<T> = {
  items?: T[];
  meta?: {
    limit: number;
    offset: number;
    count: number;
    total: number;
  };
};

type AuthProfile = {
  email: string;
  role: RoleName;
};

type LoginResponse = {
  access_token: string;
};

type DashboardState = {
  sites: SiteItem[];
  stations: StationItem[];
  sessions: SessionItem[];
  transactions: TransactionItem[];
  events: EventItem[];
  messages: MessageItem[];
  outbox: OutboxItem[];
  webhooks: WebhookItem[];
  users: UserItem[];
  simulatorState: JsonRecord | null;
  scenarios: string[];
  systemStatus: SystemStatus | null;
};

type UserState = {
  email: string;
  role: RoleName;
};

type ConnectorItem = {
  id: string;
  station_id: string;
  connector_number: number;
  state: string;
  error_code?: string | null;
};

type DetailItem<T> = {
  item: T | null;
};

type SimulatorMessage = {
  timestamp?: string;
  direction?: string;
  payload?: unknown;
};

type SelectOption = {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
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

const viewPaths: Record<DashboardView, string> = {
  overview: "/",
  sites: "/sites",
  activity: "/activity",
  simulator: "/simulator",
  sessions: "/sessions",
  admin: "/admin",
};

const pathViews: Record<string, DashboardView> = {
  "/": "overview",
  "/sites": "sites",
  "/activity": "activity",
  "/simulator": "simulator",
  "/sessions": "sessions",
  "/admin": "admin",
};

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

const scenarioCopy: Record<string, { title: string; detail: string }> = {
  "happy-path-charging-session": { title: "Happy path charging session", detail: "Boot, authorize, start, meter values, and stop." },
  "duplicate-meter-value": { title: "Duplicate meter value", detail: "Verify idempotent meter ingestion." },
  "station-offline-online": { title: "Station offline then online", detail: "Exercise recovery from a temporary disconnect." },
  "connector-fault": { title: "Connector fault", detail: "Put one connector into a faulted state." },
  "interrupted-session": { title: "Interrupted session", detail: "Simulate a session that stops unexpectedly." },
  "partner-webhook": { title: "Partner webhook", detail: "Send and validate partner delivery flow." },
  "invalid-partner-signature": { title: "Invalid partner signature", detail: "Confirm bad webhook signatures are rejected." },
  "duplicate-partner-event": { title: "Duplicate partner event", detail: "Verify duplicate partner events are ignored." },
};

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

async function requestJson<T = JsonRecord>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, {
    ...init,
    headers,
  });

  const text = await response.text();
  let data: JsonRecord | null = null;
  if (text) {
    try {
      data = JSON.parse(text) as JsonRecord;
    } catch {
      throw new ApiError(
        response.ok ? "The server returned an invalid response." : text.slice(0, 200),
        response.status,
      );
    }
  }
  if (!response.ok) {
    const detail = data?.detail ?? data?.message;
    throw new ApiError(typeof detail === "string" ? detail : response.statusText, response.status);
  }
  return data as T;
}

async function requestAllPages<T>(path: string, token: string): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;
  const limit = 200;

  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const page = await requestJson<ListResponse<T>>(
      `${path}${separator}limit=${limit}&offset=${offset}`,
      {},
      token,
    );
    const pageItems = page.items ?? [];
    items.push(...pageItems);
    const total = page.meta?.total ?? items.length;
    if (!pageItems.length || items.length >= total) break;
    offset += pageItems.length;
  }

  return items;
}

function formatTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function viewFromPath() {
  if (typeof window === "undefined") return "overview" as DashboardView;
  return pathViews[window.location.pathname] ?? "overview";
}

function titleCase(value: string | null | undefined) {
  if (!value) return "—";
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function simulatorDirectionLabel(direction: string | null | undefined) {
  if (direction === "outbound") return "Sent by simulator";
  if (direction === "inbound") return "Received by simulator";
  if (direction === "error") return "Blocked";
  if (direction === "info") return "Simulator";
  return titleCase(direction ?? "event");
}

function shortId(value: string | null | undefined) {
  if (!value) return "—";
  return value.length > 14 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function describeMessage(action: string | null | undefined) {
  const labels: Record<string, { title: string; detail: string }> = {
    StatusNotification: { title: "Connector status update", detail: "A station reported a connector state change." },
    MeterValues: { title: "Meter reading received", detail: "Energy usage data arrived for an active session." },
    StartTransaction: { title: "Charging session started", detail: "A driver or simulator began a charging transaction." },
    StopTransaction: { title: "Charging session stopped", detail: "A charging transaction ended and is ready for reconciliation." },
    BootNotification: { title: "Station booted", detail: "A charge point connected and announced itself." },
    Heartbeat: { title: "Station heartbeat", detail: "A station confirmed it is still reachable." },
  };
  return labels[action ?? ""] ?? { title: titleCase(action), detail: "OCPP message received from a station." };
}

function describeSimulatorPayload(payload: unknown) {
  if (typeof payload === "string") return payload;
  if (Array.isArray(payload)) {
    const [messageType, messageId, actionOrCode, bodyOrMessage] = payload;
    if (messageType === 2) return `${String(actionOrCode)} request ${shortId(String(messageId))}`;
    if (messageType === 3) return `Accepted ${shortId(String(messageId))}: ${JSON.stringify(bodyOrMessage)}`;
    if (messageType === 4) return `Rejected ${shortId(String(messageId))}: ${String(actionOrCode)} ${String(bodyOrMessage ?? "")}`;
  }
  if (payload && typeof payload === "object") {
    const record = payload as JsonRecord;
    if (typeof record.message === "string") return record.message;
    if (typeof record.detail === "string") return record.detail;
    if (typeof record.status_code === "number") return `HTTP ${record.status_code}: ${String(record.body ?? "")}`;
  }
  return JSON.stringify(payload);
}

function describeEvent(event: EventItem) {
  const action = String(event.action ?? event.event_type ?? "event");
  const labels: Record<string, string> = {
    seed_demo_data: "Demo data was created for this environment.",
    station_boot: "A station connected and sent a boot notification.",
    station_heartbeat_missed: "A station missed its heartbeat window and was marked offline.",
    connector_available: "An operator marked a connector available.",
    connector_unavailable: "An operator marked a connector unavailable.",
    state_transition: "A resource changed state.",
    partner_webhook: "A partner webhook event was processed.",
    create_user: "An admin user created an account.",
    retry_outbox_event: "An admin queued a failed outbox item for retry.",
    ack_dead_letter: "An admin acknowledged a dead-lettered outbox item.",
  };
  return labels[action] ?? `${titleCase(action)} on ${titleCase(event.entity_type)}`;
}

function metricStatus(value: string | null | undefined) {
  if (!value || value === "unknown") return "Not configured";
  return titleCase(value);
}

function systemDetail(status: SystemStatus | null, key: "worker" | "cache") {
  if (key === "worker") {
    if (status?.worker_detail) return status.worker_detail;
    if (!status?.worker || status.worker === "unknown") return "Worker not configured locally";
    return "Worker status reported by metrics";
  }
  if (status?.cache_detail) return status.cache_detail;
  if (!status?.cache || status.cache === "unknown") return "Cache unreachable";
  return status.cache === "ok" ? "Cache reachable" : "Cache unreachable";
}

function isStationUsable(station: StationItem | undefined) {
  return Boolean(station?.online && station.state !== "offline" && station.state !== "faulted");
}

function isConnectorUsable(connector: ConnectorItem | undefined, station: StationItem | undefined) {
  return Boolean(isStationUsable(station) && connector?.state === "available");
}

function connectorDisplayState(connector: ConnectorItem | undefined, station: StationItem | undefined) {
  if (!connector) return "—";
  if (!isStationUsable(station)) return "blocked";
  return connector.state;
}

function connectorDisplayLabel(connector: ConnectorItem | undefined, station: StationItem | undefined) {
  if (!connector) return "—";
  if (!isStationUsable(station)) return "Station offline";
  return titleCase(connector.state);
}

function connectorBlockedReason(connector: ConnectorItem | undefined, station: StationItem | undefined) {
  if (!station) return "Select a station before running a simulator scenario.";
  if (!isStationUsable(station)) return `${station.label} is offline or faulted. Bring it online before starting a simulated charge.`;
  if (!connector) return "Select a connector before running a simulator scenario.";
  if (connector.state !== "available") return `Connector ${connector.connector_number} is ${titleCase(connector.state)} and cannot start a new simulated charge.`;
  return null;
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
    <Image
      className={`elephant-logo ${className}`}
      src="/assets/brand/elephant-logo.png"
      width={256}
      height={256}
      alt="OCPP-Demo elephant logo"
      priority
      unoptimized
    />
  );
}

function BrandLink({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-link ${compact ? "compact" : ""}`}>
      <button type="button" className="logo-refresh" onClick={() => window.location.reload()} aria-label="Refresh page">
        <ElephantLogo />
      </button>
      {!compact ? <span>OCPP-Demo</span> : null}
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

function GlassSelect({
  label,
  value,
  options,
  open,
  onOpen,
  onChange,
}: {
  label: string;
  value: string;
  options: SelectOption[];
  open: boolean;
  onOpen: () => void;
  onChange: (value: string) => void;
}) {
  const selected = options.find((option) => option.value === value);
  return (
    <div className={`glass-select ${open ? "open" : ""}`}>
      <button type="button" className="glass-select-trigger" onClick={onOpen} aria-expanded={open}>
        <span>
          <small>{label}</small>
          <strong>{selected?.label ?? "Select"}</strong>
        </span>
        <span aria-hidden="true">⌄</span>
      </button>
      {open ? (
        <div className="glass-select-menu" role="listbox">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={option.value === value ? "selected" : ""}
              disabled={option.disabled}
              onClick={() => onChange(option.value)}
            >
              <strong>{option.label}</strong>
              {option.description ? <small>{option.description}</small> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
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
          <p>OCPP operations demo.</p>
        </div>
      </aside>

      <section className="login-card">
        <div className="login-card-top">
          <div className="eyebrow">overview</div>
          <h1>OCPP-Demo</h1>
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
  const [health, setHealth] = useState<HealthState>({});
  const [ready, setReady] = useState<ReadyState>({});
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [selectedStationId, setSelectedStationId] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedConnectorId, setSelectedConnectorId] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState("happy-path-charging-session");
  const [scenarioSpeed, setScenarioSpeed] = useState("normal");
  const [stationDetail, setStationDetail] = useState<DetailItem<StationDetailItem>>({ item: null });
  const [sessionDetail, setSessionDetail] = useState<DetailItem<SessionDetailItem>>({ item: null });
  const [transactionDetail, setTransactionDetail] = useState<DetailItem<TransactionDetailItem>>({ item: null });
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);
  const [newUser, setNewUser] = useState<{ email: string; password: string; role: RoleName; display_name: string }>({ email: "", password: "", role: "operator", display_name: "" });
  const [newStationToken, setNewStationToken] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [openSelect, setOpenSelect] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<DashboardView>(() => viewFromPath());

  function navigateView(view: DashboardView) {
    setActiveView(view);
    setOpenSelect(null);
    const nextPath = viewPaths[view];
    if (window.location.pathname !== nextPath) {
      window.history.pushState({ view }, "", nextPath);
    }
  }

  function selectStation(stationId: string) {
    const station = state.stations.find((item) => item.id === stationId);
    setSelectedStationId(stationId);
    if (station) setSelectedSiteId(station.site_id);
  }

  function clearSession(message = "Session expired. Sign in again.") {
    window.localStorage.removeItem("ocpp-token");
    setToken(null);
    setUser(null);
    setError(message);
  }

  async function loadDashboard(accessToken: string, role: RoleName) {
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
    ] = await Promise.all([
      requestAllPages<SiteItem>("/api/sites", accessToken),
      requestAllPages<StationItem>("/api/stations", accessToken),
      requestAllPages<SessionItem>("/api/sessions", accessToken),
      requestAllPages<TransactionItem>("/api/transactions", accessToken),
      requestAllPages<EventItem>("/api/events", accessToken),
      requestAllPages<MessageItem>("/api/messages", accessToken),
      requestAllPages<OutboxItem>("/api/outbox", accessToken),
      requestAllPages<WebhookItem>("/api/webhooks", accessToken),
      role === "admin" ? requestJson<UserItem[]>("/api/admin/users", {}, accessToken) : Promise.resolve([] as UserItem[]),
    ]);

    setState({
      sites,
      stations,
      sessions,
      transactions,
      events,
      messages,
      outbox,
      webhooks,
      users: Array.isArray(users) ? users : [],
      scenarios: predefinedScenarios,
      simulatorState: null,
      systemStatus: null,
    });

    const [healthResult, readyResult, statusResult, scenariosResult, simulatorResult] = await Promise.allSettled([
      requestJson<HealthState>("/api/health"),
      requestJson<ReadyState>("/api/ready"),
      requestJson<SystemStatus>("/api/metrics/status"),
      requestJson<{ scenarios?: string[] }>("/simulator/scenarios", {}, accessToken),
      requestJson<JsonRecord>("/simulator/state", {}, accessToken),
    ]);
    if (healthResult.status === "fulfilled") setHealth(healthResult.value);
    if (readyResult.status === "fulfilled") setReady(readyResult.value);
    setState((current) => ({
      ...current,
      systemStatus: statusResult.status === "fulfilled" ? statusResult.value : current.systemStatus,
      scenarios:
        scenariosResult.status === "fulfilled" && scenariosResult.value.scenarios?.length
          ? scenariosResult.value.scenarios
          : current.scenarios,
      simulatorState:
        simulatorResult.status === "fulfilled" ? simulatorResult.value : current.simulatorState,
    }));
    setActionError(null);
  }

  useEffect(() => {
    const handlePopState = () => setActiveView(viewFromPath());
    window.addEventListener("popstate", handlePopState);
    const storedToken = window.localStorage.getItem("ocpp-token");
    if (!storedToken) {
      setLoading(false);
      return () => window.removeEventListener("popstate", handlePopState);
    }

    setToken(storedToken);
    requestJson<AuthProfile>("/api/auth/me", {}, storedToken)
      .then(async (profile) => {
        setUser(profile);
        try {
          await loadDashboard(storedToken, profile.role);
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) clearSession();
          else setActionError(err instanceof Error ? err.message : "Dashboard data is temporarily unavailable.");
        }
      })
      .catch(() => {
        clearSession();
      })
      .finally(() => setLoading(false));

    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!state.sites.length) return;
    const nextSiteId = selectedSiteId ?? state.sites[0].id;
    if (!selectedSiteId) setSelectedSiteId(nextSiteId);
    if (!selectedStationId || !state.stations.some((station) => station.id === selectedStationId && station.site_id === nextSiteId)) {
      setSelectedStationId(state.stations.find((station) => station.site_id === nextSiteId)?.id ?? state.stations[0]?.id ?? null);
    }
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
  const simulatorStationOptions = siteStations.length ? siteStations : state.stations;
  const siteSessions = useMemo(
    () => state.sessions.filter((session) => session.site_id === selectedSite?.id),
    [state.sessions, selectedSite?.id],
  );
  const stationMessages = useMemo(
    () => state.messages.filter((message) => message.station_id === selectedStation?.id).slice(0, 6),
    [state.messages, selectedStation?.id],
  );
  const sessionTransaction = selectedSession?.transaction ?? null;
  const selectedTransaction = sessionTransaction
    ? state.transactions.find((txn) => txn.id === sessionTransaction.id) ?? sessionTransaction
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
  const connectorRunBlocker = connectorBlockedReason(selectedConnector, selectedStation);
  const canRunSelectedScenario = selectedScenario.includes("partner") || !connectorRunBlocker;

  useEffect(() => {
    if (!token || !selectedStation?.id) return;
    requestJson<ListResponse<ConnectorItem>>(`/api/stations/${selectedStation.id}/connectors`, {}, token)
      .then((result) => {
        const nextConnectors = result.items ?? [];
        setConnectors(nextConnectors);
        const preferredConnector = nextConnectors.find((connector) => isConnectorUsable(connector, selectedStation)) ?? nextConnectors[0] ?? null;
        setSelectedConnectorId(preferredConnector?.id ?? null);
      })
      .catch(() => setConnectors([]));
    requestJson<DetailItem<StationDetailItem>>(`/api/stations/${selectedStation.id}`, {}, token)
      .then((result) => setStationDetail(result))
      .catch(() => setStationDetail({ item: null }));
  }, [selectedStation?.id, token]);

  useEffect(() => {
    if (!token || !selectedSession?.id) return;
    requestJson<DetailItem<SessionDetailItem>>(`/api/sessions/${selectedSession.id}`, {}, token)
      .then((result) => setSessionDetail(result))
      .catch(() => setSessionDetail({ item: null }));
  }, [selectedSession?.id, token]);

  useEffect(() => {
    if (!token || !selectedTransaction?.id) return;
    requestJson<DetailItem<TransactionDetailItem>>(`/api/transactions/${selectedTransaction.id}`, {}, token)
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
            const result = await requestJson<LoginResponse>("/api/auth/login", {
              method: "POST",
              body: JSON.stringify({ email, password }),
            });
            const profile = await requestJson<AuthProfile>("/api/auth/me", {}, result.access_token);
            await loadDashboard(result.access_token, profile.role);
            window.localStorage.setItem("ocpp-token", result.access_token);
            setToken(result.access_token);
            setUser(profile);
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
  const selectedStationName = selectedStation?.label ?? "selected station";
  const selectedConnectorName = selectedConnector ? `connector ${selectedConnector.connector_number}` : "selected connector";
  const activeAdminCount = state.users.filter((item) => item.is_active && item.role === "admin").length;
  const isLastActiveAdmin = (item: UserItem) => item.is_active && item.role === "admin" && activeAdminCount <= 1;

  async function refresh() {
    if (!token || !user) return;
    try {
      await loadDashboard(token, user.role);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) clearSession();
      else {
        const message = err instanceof Error ? err.message : "Refresh failed";
        setActionError(message);
      }
    }
  }

  async function postAction(path: string, label: string, body?: unknown) {
    if (!token) {
      setActionError("Sign in required");
      return;
    }
    setActionError(null);
    try {
      await requestJson(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      }, token);
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) clearSession();
      else {
        const message = err instanceof Error ? err.message : "Action failed";
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
    if (!selectedScenario.includes("partner") && connectorRunBlocker) {
      setActionError(connectorRunBlocker);
      return;
    }
    const body = {
      site_id: selectedSite?.id ?? null,
      station_id: selectedStation?.external_id ?? null,
      connector_id: selectedConnector?.connector_number ? String(selectedConnector.connector_number) : null,
      speed: scenarioSpeed,
    };
    await postAction(`/simulator/run/${selectedScenario}`, `Running ${scenarioCopy[selectedScenario]?.title ?? titleCase(selectedScenario)}`, body);
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
              onClick={() => navigateView(item.id)}
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

            <div className="overview-density-grid">
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
                <GlassSelect
                  label="Station"
                  value={selectedStationId ?? ""}
                  options={state.stations.map((station) => ({
                    value: station.id,
                    label: station.label,
                    description: `${station.external_id ?? station.id} · ${station.online ? "Online" : "Offline"}`,
                  }))}
                  open={openSelect === "overview-station"}
                  onOpen={() => setOpenSelect(openSelect === "overview-station" ? null : "overview-station")}
                  onChange={(value) => {
                    selectStation(value);
                    setOpenSelect(null);
                  }}
                />
                <button type="button" className="ghost-button" onClick={() => navigateView("activity")}>
                  Activity
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
              {connectors.map((connector) => {
                const displayState = connectorDisplayState(connector, selectedStation);
                const isSelected = selectedConnector?.id === connector.id;
                return (
                  <button
                    key={connector.id}
                    type="button"
                    className={`connector-row ${isSelected ? "selected" : ""} ${!isStationUsable(selectedStation) ? "station-blocked" : ""}`}
                    onClick={() => setSelectedConnectorId(connector.id)}
                  >
                    <span className="connector-number">{String(connector.connector_number).padStart(2, "0")}</span>
                    <span className={`status-pill ${displayState}`}>{connectorDisplayLabel(connector, selectedStation).toUpperCase()}</span>
                    <span>{selectedSession?.external_session_id ?? "—"}</span>
                    <span>{connector.state === "charging" ? "32.4 kW" : "0 kW"}</span>
                    <span className={isSelected ? "selected-marker" : ""}>{isSelected ? "Selected" : formatTime(selectedStation?.last_seen_at)}</span>
                  </button>
                );
              })}
                {!connectors.length ? <EmptyState label="No connectors reported for this station." /> : null}
              </div>
            </div>

            <div className="station-bottom">
              <div className="recent-messages">
                <h3>Recent messages</h3>
                {stationMessages.map((message) => (
                  <div key={message.id} className="message-line">
                    <span>{formatTime(message.received_at)}</span>
                    <strong>{describeMessage(message.action).title}</strong>
                    <small>{describeMessage(message.action).detail} Message {shortId(message.message_id)}</small>
                  </div>
                ))}
                {!stationMessages.length ? <EmptyState label="No station messages yet." /> : null}
                <button type="button" className="text-link" onClick={() => navigateView("activity")}>
                  View all messages →
                </button>
              </div>

              <div className="station-actions">
                <h3>Actions</h3>
                <div className="action-section">
                  <span>Connector state</span>
                  <button type="button" className="ghost-button action-button" disabled={!selectedConnector} onClick={() => selectedConnector && confirmAndPost(`/api/admin/connectors/${selectedConnector.id}/available`, "Mark connector available", `Mark ${selectedConnectorName} as available so it can accept a charging session.`)}>
                    <strong>Mark {selectedConnectorName} available</strong>
                    <small>Use after a connector has recovered.</small>
                  </button>
                  <button type="button" className="ghost-button action-button" disabled={!selectedConnector} onClick={() => selectedConnector && confirmAndPost(`/api/admin/connectors/${selectedConnector.id}/unavailable`, "Mark connector unavailable", `Mark ${selectedConnectorName} as unavailable so it is kept out of service.`)}>
                    <strong>Mark {selectedConnectorName} unavailable</strong>
                    <small>Keep this connector out of service.</small>
                  </button>
                </div>
                <div className="action-section">
                  <span>Audit-only simulator records</span>
                  <button type="button" className="ghost-button action-button" onClick={() => selectedStation && confirmAndPost("/api/admin/simulator/remote-start", "Record simulated start", `Record a simulated start audit event for ${selectedStationName}. This does not contact the station or send an OCPP command.`)}>
                    <strong>Record simulated start</strong>
                    <small>Audit-only; no outbound OCPP command.</small>
                  </button>
                  <button type="button" className="ghost-button action-button" onClick={() => selectedStation && confirmAndPost("/api/admin/simulator/remote-stop", "Record simulated stop", `Record a simulated stop audit event for ${selectedStationName}. This does not contact the station or send an OCPP command.`)}>
                    <strong>Record simulated stop</strong>
                    <small>Audit-only; no outbound OCPP command.</small>
                  </button>
                </div>
                <button type="button" className="ghost-button action-button" onClick={() => navigateView("activity")}>
                  <strong>Open activity log</strong>
                  <small>Review station messages and events.</small>
                </button>
              </div>
            </div>

            <div className="connector-drawer">
              <div className="drawer-head">
                <span>Connector detail</span>
                <strong>{selectedConnector ? `#${selectedConnector.connector_number}` : "None selected"}</strong>
              </div>
              <p>Status {titleCase(selectedConnector?.state)}</p>
              {!isStationUsable(selectedStation) ? <p>Station is offline, so this connector is blocked from new sessions. Last known connector state is preserved.</p> : null}
              <p>{selectedConnector?.error_code ? `Fault ${selectedConnector.error_code}` : "No connector fault reported."}</p>
              <p>Station {selectedStation?.label ?? shortId(selectedConnector?.station_id)}</p>
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
                  <span className="timeline-tag">{titleCase(event.action)}</span>
                  <span className="timeline-text">{describeEvent(event)} {event.entity_id ? `Ref ${shortId(event.entity_id)}` : ""}</span>
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
              <div>
                <span>Total stations</span>
                <strong>{state.stations.length}</strong>
              </div>
            </div>
            <div className="sites-workspace">
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
              <div className="site-detail-panel">
                <div className="site-detail-head">
                  <div>
                    <span>Selected site</span>
                    <strong>{selectedSite?.label ?? "—"}</strong>
                  </div>
                  <div>
                    <span>Active sessions</span>
                    <strong>{siteSessions.length}</strong>
                  </div>
                </div>
                <div className="station-list">
                  {siteStations.map((station) => (
                    <button
                      key={station.id}
                      type="button"
                      className={`station-row ${selectedStation?.id === station.id ? "selected" : ""}`}
                      onClick={() => setSelectedStationId(station.id)}
                    >
                      <span>
                        <strong>{station.label}</strong>
                        <small>{station.external_id}</small>
                      </span>
                      <span>{station.online ? "Online" : "Offline"}</span>
                      <span>{station.connector_count ?? "—"} connectors</span>
                    </button>
                  ))}
                  {!siteStations.length ? <EmptyState label="No stations assigned to this site." /> : null}
                </div>
              </div>
            </div>
          </Surface> : null}

          {activeView === "simulator" ? <Surface tone="dark" className="simulator-card" id="simulator">
            <div className="card-head">
              <div>
                <div className="eyebrow">simulator</div>
                <h2>Scenarios</h2>
              </div>
            </div>
            <div className="simulator-workspace">
              <div>
                <div className="user-form simulator-form">
                  <GlassSelect
                    label="Site"
                    value={selectedSiteId ?? ""}
                    options={state.sites.map((site) => ({ value: site.id, label: site.label, description: site.is_active ? "Active site" : "Inactive site" }))}
                    open={openSelect === "site"}
                    onOpen={() => setOpenSelect(openSelect === "site" ? null : "site")}
                    onChange={(value) => {
                      setSelectedSiteId(value);
                      setSelectedStationId(state.stations.find((station) => station.site_id === value)?.id ?? null);
                      setOpenSelect(null);
                    }}
                  />
                  <GlassSelect
                    label="Station"
                    value={selectedStationId ?? ""}
                    options={simulatorStationOptions.map((station) => ({ value: station.id, label: station.label, description: `${station.external_id ?? station.id} · ${station.online ? "Online" : "Offline"}` }))}
                    open={openSelect === "station"}
                    onOpen={() => setOpenSelect(openSelect === "station" ? null : "station")}
                    onChange={(value) => {
                      selectStation(value);
                      setOpenSelect(null);
                    }}
                  />
                  <GlassSelect
                    label="Connector"
                    value={selectedConnectorId ?? ""}
                    options={connectors.map((connector) => ({
                      value: connector.id,
                      label: `Connector ${connector.connector_number}`,
                      description: isConnectorUsable(connector, selectedStation) ? "Available for simulation" : connectorDisplayLabel(connector, selectedStation),
                      disabled: !isConnectorUsable(connector, selectedStation),
                    }))}
                    open={openSelect === "connector"}
                    onOpen={() => setOpenSelect(openSelect === "connector" ? null : "connector")}
                    onChange={(value) => {
                      setSelectedConnectorId(value);
                      setOpenSelect(null);
                    }}
                  />
                  <GlassSelect
                    label="Speed"
                    value={scenarioSpeed}
                    options={[
                      { value: "slow", label: "Slow", description: "Useful for demos" },
                      { value: "normal", label: "Normal", description: "Default timing" },
                      { value: "fast", label: "Fast", description: "Run quickly" },
                    ]}
                    open={openSelect === "speed"}
                    onOpen={() => setOpenSelect(openSelect === "speed" ? null : "speed")}
                    onChange={(value) => {
                      setScenarioSpeed(value);
                      setOpenSelect(null);
                    }}
                  />
                </div>
                <div className="scenario-list">
                  {state.scenarios.map((scenario) => (
                    <button key={scenario} type="button" className={`scenario-chip ${selectedScenario === scenario ? "selected" : ""}`} onClick={() => setSelectedScenario(scenario)}>
                      <strong>{scenarioCopy[scenario]?.title ?? titleCase(scenario)}</strong>
                      <span>{scenarioCopy[scenario]?.detail ?? "Run this simulator path."}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="simulator-side-panel">
                <div className="simulator-status">{state.simulatorState?.running === true ? "Simulation running..." : "Ready"}</div>
                {connectorRunBlocker && !selectedScenario.includes("partner") ? <div className="simulator-blocker">{connectorRunBlocker}</div> : null}
                <div className="simulator-preview">
                  <button type="button" className="ghost-button" disabled={!canRunSelectedScenario} onClick={runScenario}>
                    Run simulation
                  </button>
                  <button type="button" className="danger-button" onClick={() => postAction("/api/admin/simulator/remote-stop", "Simulated stop audit recorded")}>
                    Record stop audit
                  </button>
                  <small>This records an admin audit event only; it does not interrupt a running scenario.</small>
                </div>
                <div className="timeline simulator-timeline">
                  {simulatorMessages.map((entry, index) => (
                    <div key={`${entry.timestamp}-${index}`} className="timeline-row">
                      <span className="timeline-time">{formatTime(entry.timestamp)}</span>
                      <span className="timeline-tag">{simulatorDirectionLabel(entry.direction)}</span>
                      <span className="timeline-text">{describeSimulatorPayload(entry.payload)}</span>
                    </div>
                  ))}
                  {!simulatorMessages.length ? <EmptyState label="No simulator messages yet." /> : null}
                </div>
              </div>
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
              {(sessionDetail.item?.meter_values ?? []).map((entry) => (
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
                  <strong>{titleCase(event.entity_type)}</strong>
                  <small>{describeEvent(event)}</small>
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
                <h2>Admin console</h2>
              </div>
            </div>
            <div className="admin-desktop-grid">
              <div className="admin-ops-column">
                <div className="admin-actions">
                  <h3>Operations</h3>
                  <button type="button" className="ghost-button action-button" onClick={() => confirmAndPost("/api/admin/simulator/remote-start", "Record simulated start", "This writes an admin audit event only. It does not contact the simulator, manage a WebSocket connection, or send RemoteStartTransaction.")}>
                    <strong>Record simulated start</strong>
                    <small>Audit-only simulator action.</small>
                  </button>
                  <button type="button" className="ghost-button action-button" onClick={() => confirmAndPost("/api/admin/simulator/remote-stop", "Record simulated stop", "This writes an admin audit event only. It does not contact the simulator, manage a WebSocket connection, or send RemoteStopTransaction.")}>
                    <strong>Record simulated stop</strong>
                    <small>Audit-only simulator action.</small>
                  </button>
                  <button type="button" className="ghost-button action-button" onClick={() => selectedOutboxId && confirmAndPost(`/api/admin/outbox/${selectedOutboxId}/retry`, "Retry failed outbox", `This requeues outbox item ${shortId(selectedOutboxId)} for delivery. Use it after fixing the cause of a failed webhook or downstream delivery.`)}>
                    <strong>Retry failed outbox item</strong>
                    <small>Requeue the oldest visible failed item.</small>
                  </button>
                  <button type="button" className="ghost-button action-button" onClick={() => selectedOutboxId && confirmAndPost(`/api/admin/outbox/${selectedOutboxId}/ack`, "Acknowledge dead letter", `This marks outbox item ${shortId(selectedOutboxId)} as manually reviewed. It should only be used when retry is no longer appropriate.`)}>
                    <strong>Acknowledge dead letter</strong>
                    <small>Mark reviewed when retry is no longer needed.</small>
                  </button>
                </div>

                {isAdmin ? (
                  <div className="admin-station-tools">
                    <h3>Station controls</h3>
                    <div className="user-form station-state-form">
                      <GlassSelect
                        label="Station"
                        value={selectedStationId ?? ""}
                        options={state.stations.map((station) => ({
                          value: station.id,
                          label: station.label,
                          description: `${station.external_id ?? station.id} · ${station.online ? "Online" : "Offline"}`,
                        }))}
                        open={openSelect === "station-state"}
                        onOpen={() => setOpenSelect(openSelect === "station-state" ? null : "station-state")}
                        onChange={(value) => {
                          selectStation(value);
                          setOpenSelect(null);
                        }}
                      />
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={!selectedStation || selectedStation.online}
                        onClick={() => {
                          if (!selectedStation) return;
                          confirmAndPost(
                            `/api/admin/stations/${selectedStation.id}/online`,
                            "Set station online",
                            `Mark ${selectedStation.label} online. Connector states are not changed.`,
                          );
                        }}
                      >
                        Set online
                      </button>
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={!selectedStation || !selectedStation.online}
                        onClick={() => {
                          if (!selectedStation) return;
                          confirmAndPost(
                            `/api/admin/stations/${selectedStation.id}/offline`,
                            "Set station offline",
                            `Mark ${selectedStation.label} offline and block new simulated sessions. Connector states are preserved.`,
                          );
                        }}
                      >
                        Set offline
                      </button>
                    </div>
                    <div className="user-form station-token-form">
                      <GlassSelect
                        label="Station token"
                        value={selectedStationId ?? ""}
                        options={state.stations.map((station) => ({
                          value: station.id,
                          label: station.label,
                          description: station.external_id,
                        }))}
                        open={openSelect === "station-token-rotate"}
                        onOpen={() => setOpenSelect(openSelect === "station-token-rotate" ? null : "station-token-rotate")}
                        onChange={(value) => {
                          selectStation(value);
                          setOpenSelect(null);
                        }}
                      />
                      <input
                        type="password"
                        autoComplete="new-password"
                        placeholder="New station token (32+ characters)"
                        value={newStationToken}
                        onChange={(event) => setNewStationToken(event.target.value)}
                      />
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={!selectedStation || newStationToken.length < 32}
                        onClick={() => {
                          if (!selectedStation) return;
                          confirmAndPost(
                            `/api/admin/stations/${selectedStation.id}/token`,
                            "Rotate station token",
                            `Replace the OCPP token for ${selectedStation.label}. The station must use the new token on its next connection.`,
                            { token: newStationToken },
                          );
                          setNewStationToken("");
                        }}
                      >
                        Rotate station token
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>

            {isAdmin ? (
              <div className="user-admin">
                <h3>Users and roles</h3>
                <div className="user-table">
                  {state.users.map((item) => (
                    <div key={item.id} className={`user-row admin-user-row ${item.is_active ? "" : "inactive"}`}>
                      <span>
                        <strong>{item.email}</strong>
                        <small>{item.display_name || (item.email === user.email ? "Current user" : "No display name")}</small>
                        <small>Created {formatDateTime(item.created_at)} · Last login {item.last_login_at ? formatDateTime(item.last_login_at) : "not tracked yet"}</small>
                      </span>
                      <span className={`account-badge ${item.is_active ? "active" : "disabled"}`}>{item.is_active ? "Active" : "Disabled"}</span>
                      <strong>{titleCase(item.role)}</strong>
                      <div className="user-row-actions">
                        <button
                          type="button"
                          className="mini-button"
                          disabled={!item.is_active || item.email === user.email || isLastActiveAdmin(item)}
                          title={isLastActiveAdmin(item) ? "This is the last active admin." : undefined}
                          onClick={() => confirmAndPost(`/api/admin/users/${item.id}/role`, item.role === "admin" ? "Make operator" : "Make admin", item.role === "admin" ? `This demotes ${item.email} to operator. They will lose user management and recovery permissions, but can still inspect and run safe operations.` : `This promotes ${item.email} to admin. They will be able to manage users and perform recovery actions.`, { role: item.role === "admin" ? "operator" : "admin" })}
                        >
                          {item.role === "admin" ? "Make operator" : "Make admin"}
                        </button>
                        <button
                          type="button"
                          className="mini-button"
                          disabled={item.email === user.email || isLastActiveAdmin(item)}
                          title={isLastActiveAdmin(item) ? "This is the last active admin." : undefined}
                          onClick={() => confirmAndPost(`/api/admin/users/${item.id}/${item.is_active ? "deactivate" : "activate"}`, item.is_active ? "Remove user" : "Restore user", item.is_active ? `This disables ${item.email}. They will no longer be able to sign in, and existing bearer tokens will be rejected on their next request. Audit history is kept.` : `This restores ${item.email}. They will be able to sign in again using their existing password and current role.`)}
                        >
                          {item.is_active ? "Remove" : "Restore"}
                        </button>
                      </div>
                    </div>
                  ))}
                  {!state.users.length ? <EmptyState label="No users loaded." /> : null}
                </div>
                <div className="user-form">
                  <input placeholder="email" value={newUser.email} onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))} />
                  <input placeholder="password" type="password" value={newUser.password} onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))} />
                  <GlassSelect
                    label="Role"
                    value={newUser.role}
                    options={[
                      { value: "operator", label: "Operator", description: "Can inspect and run safe operations" },
                      { value: "admin", label: "Admin", description: "Can manage users and recovery actions" },
                    ]}
                    open={openSelect === "role"}
                    onOpen={() => setOpenSelect(openSelect === "role" ? null : "role")}
                    onChange={(value) => {
                      setNewUser((current) => ({ ...current, role: value as RoleName }));
                      setOpenSelect(null);
                    }}
                  />
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => confirmAndPost("/api/admin/users", "Create user", `This creates ${newUser.email || "a new user"} with ${newUser.role} access. Share the password through a secure channel and rotate it if it was entered on a shared screen.`, newUser)}
                  >
                    Create user
                  </button>
                  <button type="button" className="ghost-button user-form-wide" disabled title="Rotate the partner webhook secret by updating deploy/.env and restarting the stack.">
                    Rotate webhook secret
                  </button>
                </div>
              </div>
            ) : null}
            </div>
          </Surface> : null}

          {activeView === "admin" ? <Surface tone="dark" className="system-card" id="system">
            <div className="card-head">
              <div>
                <div className="eyebrow">system</div>
                <h2>System health</h2>
              </div>
            </div>
            <div className="system-grid">
              <Metric label="API" value={metricStatus(health.status)} subtext={!health.status ? "No health response yet" : "API responding"} />
              <Metric label="Worker" value={metricStatus(state.systemStatus?.worker ?? health.worker)} subtext={systemDetail(state.systemStatus, "worker")} />
              <Metric label="Cache" value={metricStatus(state.systemStatus?.cache ?? health.cache)} subtext={systemDetail(state.systemStatus, "cache")} />
              <Metric label="Outbox" value={`${state.outbox.length}`} subtext={outboxRetrying ? "Outbox has retrying work" : "Outbox retry worker idle"} />
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
