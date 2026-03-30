import { useEffect, useMemo, useState } from 'react'
import { listen } from '@tauri-apps/api/event'
import { Popover } from '@/components/Popover/Popover'
import { SettingsPanel } from '@/components/Settings/SettingsPanel'
import { FloatingSettingsButton } from '@/components/FloatingBtn/FloatingSettingsButton'
import { usePopover } from '@/hooks/usePopover'
import { useTranslate } from '@/hooks/useTranslate'
import { loadSettings, saveSettings } from '@/services/config'
import { DEFAULT_SETTINGS, type AppSettings } from '@/types/settings'

interface SelectionEventPayload {
  text: string
  trigger: 'auto' | 'shortcut'
}

interface HotkeyTranslationPayload {
  translated: string
}

export function App() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeFieldValue, setActiveFieldValue] = useState('xin chao')
  const [statusMessage, setStatusMessage] = useState('Ready')
  const { state, data, error, close, openFromSelection } = usePopover(settings)
  const { status: translateStatus, runTranslate, error: translateError } = useTranslate()

  useEffect(() => {
    let mounted = true
    const setup = async () => {
      try {
        const current = await loadSettings()
        if (mounted) {
          setSettings(current)
        }
      } catch {
        if (mounted) {
          setStatusMessage('Using default settings')
        }
      }
    }
    void setup()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let cleanupSelection: (() => void) | null = null
    let cleanupHotkey: (() => void) | null = null
    const setupEvents = async () => {
      try {
        const unlistenSelection = await listen<SelectionEventPayload>('selection-changed', (event) => {
          void openFromSelection(event.payload.text, event.payload.trigger)
        })
        cleanupSelection = unlistenSelection
      } catch {
        cleanupSelection = null
      }
      try {
        const unlistenHotkey = await listen<HotkeyTranslationPayload>('hotkey-translated', (event) => {
          setActiveFieldValue(event.payload.translated)
          setStatusMessage('Field replaced from global hotkey')
        })
        cleanupHotkey = unlistenHotkey
      } catch {
        cleanupHotkey = null
      }
    }
    void setupEvents()
    return () => {
      cleanupSelection?.()
      cleanupHotkey?.()
    }
  }, [openFromSelection])

  const selectedWordCount = useMemo(() => {
    if (!data.selectedText) {
      return 0
    }
    return data.selectedText.trim().split(/\s+/).filter(Boolean).length
  }, [data.selectedText])

  const handleSelection = () => {
    const selectedText = window.getSelection()?.toString().trim() ?? ''
    if (!selectedText) {
      return
    }
    void openFromSelection(selectedText, 'auto')
  }

  const handleSaveSettings = async () => {
    try {
      const saved = await saveSettings(settings)
      setSettings(saved)
      setSettingsOpen(false)
      setStatusMessage('Settings saved')
    } catch {
      setStatusMessage('Failed to save settings')
    }
  }

  const handleFieldTranslate = async () => {
    try {
      const source = settings.source_language
      const translated = await runTranslate(activeFieldValue, source, settings.target_language)
      setActiveFieldValue(translated.result)
      setStatusMessage(`Translated by ${translated.engine}`)
    } catch {
      setStatusMessage('Translate failed')
    }
  }

  return (
    <main className="apl-app-shell">
      <section className="apl-hero">
        <h1>DictOver Desktop</h1>
        <p>Step 2 core app shell with popover lookup, quick translation, settings, and CI-ready structure.</p>
      </section>

      <section className="apl-card" onMouseUp={handleSelection}>
        <h2>Selection Probe</h2>
        <p data-testid="selectable-text">
          Select one word for dictionary lookup or multiple words for translation. The popover state machine follows idle,
          loading, lookup, translate, error.
        </p>
        <button type="button" onClick={() => void openFromSelection('xin chao', 'shortcut')}>
          Trigger Shortcut Mode Sample
        </button>
        <p>Words selected: {selectedWordCount}</p>
      </section>

      <section className="apl-card">
        <h2>Hotkey Translation Field</h2>
        <input
          data-testid="translate-field"
          value={activeFieldValue}
          onChange={(event) => setActiveFieldValue(event.target.value)}
        />
        <button type="button" onClick={() => void handleFieldTranslate()}>
          Translate Active Field
        </button>
        <p>{statusMessage}</p>
        {translateStatus === 'error' && <p className="apl-error">{translateError}</p>}
      </section>

      <Popover
        state={state}
        selection={data.selectedText}
        dictionary={data.dictionary}
        translation={data.translation}
        error={error}
        panelMode={settings.popover_open_panel_mode}
        onClose={close}
      />

      <SettingsPanel
        open={settingsOpen}
        settings={settings}
        onChange={setSettings}
        onSave={handleSaveSettings}
        onClose={() => setSettingsOpen(false)}
      />

      <FloatingSettingsButton onClick={() => setSettingsOpen(true)} />
    </main>
  )
}
