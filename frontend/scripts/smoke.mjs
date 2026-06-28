import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = process.cwd();
const page = readFileSync(resolve(root, "app/page.tsx"), "utf8");
const styles = readFileSync(resolve(root, "app/globals.css"), "utf8");
const layout = readFileSync(resolve(root, "app/layout.tsx"), "utf8");

const requiredScreens = [
  "Overview",
  "Sites",
  "Activity",
  "Sessions",
  "Simulator",
  "Admin & system",
  "Live events",
  "Message payload",
  "Health and observability",
];

const requiredScenarios = [
  "happy-path-charging-session",
  "duplicate-meter-value",
  "station-offline-online",
  "connector-fault",
  "interrupted-session",
  "partner-webhook",
  "invalid-partner-signature",
  "duplicate-partner-event",
];

const requiredUiSignals = [
  "Email",
  "Password",
  "Fleet operations dashboard.",
  "© Mahmoud elfeel 2026",
  "OCPP-Demo",
  "viewPaths",
  "GlassSelect",
  "Worker not configured locally",
  "Outbox retry worker idle",
  "Cache unreachable",
  "loading-screen",
  "error",
  "confirmAndPost",
  "Connector detail",
  "connector_number ? String",
  "Retry failed outbox",
  "Acknowledge dead letter",
];

const missing = [];

for (const label of requiredScreens) {
  if (!page.includes(`label: "${label}"`) && !page.includes(`>${label}<`)) {
    missing.push(`screen:${label}`);
  }
}

for (const scenario of requiredScenarios) {
  if (!page.includes(scenario)) {
    missing.push(`scenario:${scenario}`);
  }
}

for (const signal of requiredUiSignals) {
  if (!page.includes(signal) && !styles.includes(signal)) {
    missing.push(`ui:${signal}`);
  }
}

if (!styles.includes("radial-gradient") || !styles.includes("rgba(") || !styles.includes("--shadow")) {
  missing.push("visual:liquid-glass-style");
}

for (const route of ["sites", "activity", "simulator", "sessions", "admin"]) {
  try {
    readFileSync(resolve(root, `app/${route}/page.tsx`), "utf8");
  } catch {
    missing.push(`route:/${route}`);
  }
}

if (!layout.includes("OCPP-Demo") || !layout.includes("icons")) {
  missing.push("metadata:brand-icon");
}

if (missing.length > 0) {
  console.error("Frontend smoke check failed:");
  for (const item of missing) {
    console.error(`- ${item}`);
  }
  process.exit(1);
}

console.log("frontend smoke checks passed");
