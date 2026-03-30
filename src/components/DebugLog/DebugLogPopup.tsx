import { useMemo } from "react";
import {
  clearDebugLogs,
  formatDebugLogs,
  type DebugLogEntry,
} from "@/services/debugLog";

interface DebugLogPopupProps {
  logs: DebugLogEntry[];
}

export function DebugLogPopup({ logs }: DebugLogPopupProps) {
  const text = useMemo(() => formatDebugLogs(logs), [logs]);

  const copyLogs = async () => {
    if (!text.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      return;
    }
  };

  return (
    <section className="apl-debug-log-root">
      <div className="apl-debug-log-panel" role="region" aria-label="Debug logs">
        <header className="apl-debug-log-header">
          <h3>Debug Logs ({logs.length})</h3>
          <div className="apl-debug-log-actions">
            <button type="button" onClick={() => void copyLogs()}>
              Copy
            </button>
            <button type="button" onClick={() => clearDebugLogs()}>
              Clear
            </button>
          </div>
        </header>
        <textarea
          className="apl-debug-log-text"
          readOnly
          value={text}
          placeholder="No logs yet"
        />
      </div>
    </section>
  );
}
