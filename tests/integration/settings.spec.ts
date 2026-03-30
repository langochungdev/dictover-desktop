import { describe, expect, it } from 'vitest'
import { DEFAULT_SETTINGS, sanitizeSettings } from '@/types/settings'

describe('settings sanitize', () => {
  it('clamps max definitions between 1 and 10', () => {
    const low = sanitizeSettings({ ...DEFAULT_SETTINGS, max_definitions: 0 })
    const high = sanitizeSettings({ ...DEFAULT_SETTINGS, max_definitions: 99 })
    expect(low.max_definitions).toBe(1)
    expect(high.max_definitions).toBe(10)
  })

  it('keeps default shortcut values when empty', () => {
    const input = sanitizeSettings({
      ...DEFAULT_SETTINGS,
      popover_shortcut: '',
      hotkey_translate_shortcut: ''
    })
    expect(input.popover_shortcut).toBe(DEFAULT_SETTINGS.popover_shortcut)
    expect(input.hotkey_translate_shortcut).toBe(DEFAULT_SETTINGS.hotkey_translate_shortcut)
  })
})
