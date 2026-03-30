import { invoke } from "@tauri-apps/api/core";

const SIDECAR_BASE_URL = "http://127.0.0.1:49152";

function hasTauriBridge(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function invokeWithFallback<T>(
  command: string,
  args: Record<string, unknown>,
  fallback: () => Promise<T>,
): Promise<T> {
  if (!hasTauriBridge()) {
    return fallback();
  }
  try {
    const result = await invoke<T>(command, args);
    return result;
  } catch {
    return fallback();
  }
}

export async function sidecarPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${SIDECAR_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Sidecar request failed with status ${response.status}`);
  }
  const payload = (await response.json()) as T;
  return payload;
}
