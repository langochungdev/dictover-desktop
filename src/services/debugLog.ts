export interface DebugLogEntry {
  id: string;
  at: string;
  scope: string;
  message: string;
  detail?: string;
}

const LOG_KEY = "dictover-debug-log";
const MAX_LOG_COUNT = 300;

function safeParse(raw: string | null): DebugLogEntry[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as DebugLogEntry[];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed;
  } catch {
    return [];
  }
}

export function readDebugLogs(): DebugLogEntry[] {
  if (typeof window === "undefined") {
    return [];
  }
  return safeParse(localStorage.getItem(LOG_KEY));
}

export function clearDebugLogs(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(LOG_KEY, JSON.stringify([]));
  window.dispatchEvent(new CustomEvent("dictover-debug-log-updated"));
}

export function appendDebugLog(
  scope: string,
  message: string,
  detail?: string,
): DebugLogEntry {
  const entry: DebugLogEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    at: new Date().toISOString(),
    scope,
    message,
    detail,
  };

  if (typeof window === "undefined") {
    return entry;
  }

  const current = readDebugLogs();
  const next = [...current, entry].slice(-MAX_LOG_COUNT);
  localStorage.setItem(LOG_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent("dictover-debug-log-updated"));

  return entry;
}

export function formatDebugLogs(entries: DebugLogEntry[]): string {
  return entries
    .map((entry) => {
      const timestamp = entry.at.replace("T", " ").replace("Z", "");
      const suffix = entry.detail ? ` | ${entry.detail}` : "";
      return `[${timestamp}] [${entry.scope}] ${entry.message}${suffix}`;
    })
    .join("\n");
}
