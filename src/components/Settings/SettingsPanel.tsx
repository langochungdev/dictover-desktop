import { INPUT_LANGUAGES, OUTPUT_LANGUAGES } from '@/constants/languages'
import type {
  AppSettings,
  AutoPlayAudioMode,
  PopoverDefinitionLanguageMode,
  PopoverOpenPanelMode,
  PopoverTriggerMode
} from '@/types/settings'

interface SettingsPanelProps {
  open: boolean
  settings: AppSettings
  onChange: (next: AppSettings) => void
  onSave: () => Promise<void>
  onClose: () => void
}

function setField<K extends keyof AppSettings>(settings: AppSettings, key: K, value: AppSettings[K]): AppSettings {
  return { ...settings, [key]: value }
}

export function SettingsPanel({ open, settings, onChange, onSave, onClose }: SettingsPanelProps) {
  if (!open) {
    return null
  }

  return (
    <section className="apl-settings-root" role="dialog" aria-modal="true" aria-labelledby="apl-settings-title">
      <header className="apl-settings-header">
        <h2 id="apl-settings-title">DictOver Settings</h2>
      </header>

      <div className="apl-settings-grid">
        <label><input type="checkbox" checked={settings.enable_lookup} onChange={(e) => onChange(setField(settings, 'enable_lookup', e.target.checked))} /> Enable Lookup</label>
        <label><input type="checkbox" checked={settings.enable_translate} onChange={(e) => onChange(setField(settings, 'enable_translate', e.target.checked))} /> Enable Translate</label>
        <label><input type="checkbox" checked={settings.enable_audio} onChange={(e) => onChange(setField(settings, 'enable_audio', e.target.checked))} /> Enable Audio</label>

        <label>
          Auto Play Audio
          <select value={settings.auto_play_audio_mode} onChange={(e) => onChange(setField(settings, 'auto_play_audio_mode', e.target.value as AutoPlayAudioMode))}>
            <option value="off">Off</option>
            <option value="word">Word</option>
            <option value="all">All</option>
          </select>
        </label>

        <label>
          Popover Trigger
          <select value={settings.popover_trigger_mode} onChange={(e) => onChange(setField(settings, 'popover_trigger_mode', e.target.value as PopoverTriggerMode))}>
            <option value="auto">Auto</option>
            <option value="shortcut">Shortcut</option>
          </select>
        </label>

        <label>
          Popover Shortcut
          <input
            value={settings.popover_shortcut}
            onChange={(e) => onChange(setField(settings, 'popover_shortcut', e.target.value))}
          />
        </label>

        <label>
          Source Language
          <select value={settings.source_language} onChange={(e) => onChange(setField(settings, 'source_language', e.target.value as AppSettings['source_language']))}>
            {INPUT_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
        </label>

        <label>
          Target Language
          <select value={settings.target_language} onChange={(e) => onChange(setField(settings, 'target_language', e.target.value as AppSettings['target_language']))}>
            {OUTPUT_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
        </label>

        <label>
          Max Definitions: {settings.max_definitions}
          <input
            type="range"
            min={1}
            max={10}
            value={settings.max_definitions}
            onChange={(e) => onChange(setField(settings, 'max_definitions', Number(e.target.value)))}
          />
        </label>

        <label><input type="checkbox" checked={settings.show_example} onChange={(e) => onChange(setField(settings, 'show_example', e.target.checked))} /> Show Example</label>

        <label>
          Open Panel Mode
          <select
            value={settings.popover_open_panel_mode}
            onChange={(e) => onChange(setField(settings, 'popover_open_panel_mode', e.target.value as PopoverOpenPanelMode))}
          >
            <option value="none">None</option>
            <option value="details">Details</option>
            <option value="images">Images</option>
          </select>
        </label>

        <label>
          Definition Language Mode
          <select
            value={settings.popover_definition_language_mode}
            onChange={(e) => onChange(setField(settings, 'popover_definition_language_mode', e.target.value as PopoverDefinitionLanguageMode))}
          >
            <option value="output">Output</option>
            <option value="input">Input</option>
            <option value="english">English</option>
          </select>
        </label>

        <label>
          Hotkey Translate Shortcut
          <input
            value={settings.hotkey_translate_shortcut}
            onChange={(e) => onChange(setField(settings, 'hotkey_translate_shortcut', e.target.value))}
          />
        </label>
      </div>

      <footer className="apl-settings-actions">
        <button type="button" onClick={onClose}>Cancel</button>
        <button type="button" onClick={() => void onSave()}>Save</button>
      </footer>
    </section>
  )
}
