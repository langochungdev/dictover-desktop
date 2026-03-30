import { beforeEach, describe, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";

import { loadSettings, saveSettings } from "@/services/config";
import { invokeWithFallback, sidecarPost } from "@/services/tauri";
import { DEFAULT_SETTINGS } from "@/types/settings";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

function withWindowBridge(enabled: boolean): void {
  (globalThis as unknown as { window: Record<string, unknown> }).window =
    enabled ? { __TAURI_INTERNALS__: {} } : {};
}

function installMemoryStorage(): Storage {
  const storage = new Map<string, string>();
  const localStorageMock = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => {
      storage.set(key, value);
    },
    removeItem: (key: string) => {
      storage.delete(key);
    },
    clear: () => {
      storage.clear();
    },
    key: (index: number) => Array.from(storage.keys())[index] ?? null,
    get length() {
      return storage.size;
    },
  } satisfies Storage;

  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    configurable: true,
    writable: true,
  });

  return localStorageMock;
}

describe("tauri bridge fallback", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("uses fallback when tauri bridge does not exist", async () => {
    withWindowBridge(false);
    const fallback = vi.fn().mockResolvedValue("ok");

    const output = await invokeWithFallback("unknown_cmd", {}, fallback);

    expect(output).toBe("ok");
    expect(fallback).toHaveBeenCalledOnce();
    expect(vi.mocked(invoke)).not.toHaveBeenCalled();
  });

  it("uses fallback when invoke throws", async () => {
    withWindowBridge(true);
    const mockInvoke = vi.mocked(invoke);
    mockInvoke.mockRejectedValue(new Error("invoke failed"));
    const fallback = vi.fn().mockResolvedValue("backup");

    const output = await invokeWithFallback(
      "translate_text",
      { payload: {} },
      fallback,
    );

    expect(output).toBe("backup");
    expect(fallback).toHaveBeenCalledOnce();
  });

  it("returns invoke result when invoke succeeds", async () => {
    withWindowBridge(true);
    const mockInvoke = vi.mocked(invoke);
    mockInvoke.mockResolvedValue("from-tauri");
    const fallback = vi.fn().mockResolvedValue("backup");

    const output = await invokeWithFallback(
      "translate_text",
      { payload: {} },
      fallback,
    );

    expect(output).toBe("from-tauri");
    expect(fallback).not.toHaveBeenCalled();
  });
});

describe("sidecar HTTP contracts", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("throws on non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({}),
      }),
    );

    await expect(
      sidecarPost("/translate", { text: "xin chao" }),
    ).rejects.toThrow("Sidecar request failed with status 503");
  });
});

describe("settings service fallback persistence", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    withWindowBridge(false);
    installMemoryStorage();
  });

  it("loads default settings when storage is empty", async () => {
    const output = await loadSettings();
    expect(output).toEqual(DEFAULT_SETTINGS);
  });

  it("sanitizes saved settings when loading from local storage", async () => {
    localStorage.setItem(
      "dictover-settings",
      JSON.stringify({
        ...DEFAULT_SETTINGS,
        max_definitions: 999,
        popover_shortcut: "",
        hotkey_translate_shortcut: "",
      }),
    );

    const output = await loadSettings();

    expect(output.max_definitions).toBe(10);
    expect(output.popover_shortcut).toBe(DEFAULT_SETTINGS.popover_shortcut);
    expect(output.hotkey_translate_shortcut).toBe(
      DEFAULT_SETTINGS.hotkey_translate_shortcut,
    );
  });

  it("sanitizes and stores settings during save", async () => {
    const output = await saveSettings({
      ...DEFAULT_SETTINGS,
      max_definitions: 0,
      popover_shortcut: "",
      hotkey_translate_shortcut: "",
    });

    expect(output.max_definitions).toBe(1);
    expect(output.popover_shortcut).toBe(DEFAULT_SETTINGS.popover_shortcut);
    expect(output.hotkey_translate_shortcut).toBe(
      DEFAULT_SETTINGS.hotkey_translate_shortcut,
    );
    expect(localStorage.getItem("dictover-settings")).toContain(
      '"max_definitions":1',
    );
  });
});
