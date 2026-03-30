import { describe, expect, it } from "vitest";
import { DEFAULT_SETTINGS, sanitizeSettings } from "@/types/settings";

describe("settings sanitize", () => {
  it("clamps max definitions between 1 and 10", () => {
    const low = sanitizeSettings({ ...DEFAULT_SETTINGS, max_definitions: 0 });
    const high = sanitizeSettings({ ...DEFAULT_SETTINGS, max_definitions: 99 });
    expect(low.max_definitions).toBe(1);
    expect(high.max_definitions).toBe(10);
  });

  it("keeps default shortcut values when empty", () => {
    const input = sanitizeSettings({
      ...DEFAULT_SETTINGS,
      popover_shortcut: "",
      hotkey_translate_shortcut: "",
    });
    expect(input.popover_shortcut).toBe(DEFAULT_SETTINGS.popover_shortcut);
    expect(input.hotkey_translate_shortcut).toBe(
      DEFAULT_SETTINGS.hotkey_translate_shortcut,
    );
  });

  it("falls back to defaults for invalid numeric and empty mode fields", () => {
    const input = sanitizeSettings({
      ...DEFAULT_SETTINGS,
      max_definitions: Number.NaN,
      auto_play_audio_mode: "",
      popover_trigger_mode: "",
      popover_open_panel_mode: "",
      popover_definition_language_mode: "",
    });

    expect(input.max_definitions).toBe(DEFAULT_SETTINGS.max_definitions);
    expect(input.auto_play_audio_mode).toBe(
      DEFAULT_SETTINGS.auto_play_audio_mode,
    );
    expect(input.popover_trigger_mode).toBe(
      DEFAULT_SETTINGS.popover_trigger_mode,
    );
    expect(input.popover_open_panel_mode).toBe(
      DEFAULT_SETTINGS.popover_open_panel_mode,
    );
    expect(input.popover_definition_language_mode).toBe(
      DEFAULT_SETTINGS.popover_definition_language_mode,
    );
  });
});
