import { beforeEach, describe, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { translateText } from "../../src/services/translate";
import { lookupDictionary } from "../../src/services/dictionary";
import { getActionType } from "../../src/hooks/usePopover";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

describe("Tauri IPC services", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (globalThis as unknown as { window: Record<string, unknown> }).window = {
      __TAURI_INTERNALS__: {},
    };
  });

  it("calls translate command with payload", async () => {
    const mockInvoke = vi.mocked(invoke);
    mockInvoke.mockResolvedValue({
      result: "Hello",
      engine: "argos",
      mode: "direct",
    });

    const result = await translateText({
      text: "xin chào",
      source: "vi",
      target: "en",
    });

    expect(mockInvoke).toHaveBeenCalledWith(
      "translate_text",
      expect.objectContaining({
        payload: expect.objectContaining({
          text: "xin chào",
          source: "vi",
          target: "en",
        }),
      }),
    );
    expect(result).toEqual({
      result: "Hello",
      engine: "argos",
      mode: "direct",
    });
  });

  it("calls dictionary lookup command with payload", async () => {
    const mockInvoke = vi.mocked(invoke);
    mockInvoke.mockResolvedValue({
      word: "hello",
      phonetic: null,
      audio_url: null,
      meanings: [
        { part_of_speech: "noun", definitions: ["hello"], example: null },
      ],
      provider: "wiktionary-rest",
      fallback_used: false,
    });

    const result = await lookupDictionary({ word: "hello", source_lang: "en" });

    expect(mockInvoke).toHaveBeenCalledWith(
      "lookup_dictionary",
      expect.objectContaining({
        payload: expect.objectContaining({ word: "hello", source_lang: "en" }),
      }),
    );
    expect(result.word).toBe("hello");
  });
});

describe("Popover action routing", () => {
  it("routes single word to lookup", () => {
    expect(getActionType("hello")).toBe("lookup");
  });

  it("routes multi-word text to translate", () => {
    expect(getActionType("hello world how are you")).toBe("translate");
  });
});
