import { useEffect, useState } from "react";
import { DebugLogPopup } from "@/components/DebugLog/DebugLogPopup";
import { readDebugLogs, type DebugLogEntry } from "@/services/debugLog";

export function DebugLogWindow() {
  const [logs, setLogs] = useState<DebugLogEntry[]>(() => readDebugLogs());

  useEffect(() => {
    const refresh = () => {
      setLogs(readDebugLogs());
    };
    window.addEventListener("dictover-debug-log-updated", refresh);
    return () => {
      window.removeEventListener("dictover-debug-log-updated", refresh);
    };
  }, []);

  return (
    <main className="apl-debug-window-shell">
      <DebugLogPopup logs={logs} />
    </main>
  );
}
