import { useCallback, useEffect, useRef, useState } from 'react'
import type { DictionaryResult } from '@/services/dictionary'
import type { TranslateResult } from '@/services/translate'
import type { PopoverState } from '@/hooks/usePopover'
import type { PopoverOpenPanelMode } from '@/types/settings'

interface PopoverProps {
  state: PopoverState
  selection: string
  dictionary: DictionaryResult | null
  translation: TranslateResult | null
  error: string | null
  panelMode: PopoverOpenPanelMode
  onOpenSettings?: () => void
}

function firstLookupSummary(dictionary: DictionaryResult): string {
  const firstMeaning = dictionary.meanings[0]
  if (!firstMeaning) {
    return ''
  }
  const firstDefinition = firstMeaning.definitions[0]
  return String(firstDefinition || '').trim()
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function sanitizeMarkup(value: string): string {
  const withBreaks = value
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/li>/gi, '\n')

  const withoutTags = withBreaks.replace(/<[^>]+>/g, ' ')

  if (typeof document === 'undefined') {
    return withoutTags
  }

  const element = document.createElement('textarea')
  element.innerHTML = withoutTags
  return element.value
}

function imageCandidates(query: string): string[] {
  const safeQuery = encodeURIComponent(query.trim())
  if (!safeQuery) {
    return []
  }

  return [0, 1, 2, 3].map((index) => `https://source.unsplash.com/600x420/?${safeQuery}&sig=${index}`)
}

export function Popover({
  state,
  selection,
  dictionary,
  translation,
  error,
  panelMode,
  onOpenSettings
}: PopoverProps) {
  const [activePanel, setActivePanel] = useState<PopoverOpenPanelMode>('none')
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [audioError, setAudioError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const stopAudio = useCallback(() => {
    if (!audioRef.current) {
      return
    }
    audioRef.current.pause()
    audioRef.current.currentTime = 0
    setAudioPlaying(false)
  }, [])

  useEffect(() => {
    setActivePanel(panelMode)
  }, [panelMode, selection, state])

  useEffect(() => {
    return () => {
      stopAudio()
    }
  }, [stopAudio])

  const canPlayAudio = Boolean(dictionary?.audio_url)

  const playAudio = useCallback(async () => {
    if (audioPlaying) {
      stopAudio()
      return
    }

    if (!dictionary?.audio_url) {
      setAudioError('No audio source available')
      return
    }

    setAudioError(null)
    stopAudio()

    try {
      const audio = new Audio(dictionary.audio_url)
      audioRef.current = audio
      audio.onended = () => {
        setAudioPlaying(false)
      }
      audio.onerror = () => {
        setAudioPlaying(false)
        setAudioError('Audio playback failed')
      }
      setAudioPlaying(true)
      await audio.play()
    } catch {
      setAudioPlaying(false)
      setAudioError('Audio playback failed')
    }
  }, [audioPlaying, dictionary?.audio_url, stopAudio])

  const togglePanel = useCallback((panel: PopoverOpenPanelMode) => {
    setActivePanel((current) => (current === panel ? 'none' : panel))
  }, [])

  if (state === 'idle') {
    return null
  }

  const cleanSelection = normalizeText(selection)
  const lookupSummary = dictionary ? normalizeText(sanitizeMarkup(firstLookupSummary(dictionary))) : ''
  const translationLines = translation
    ? sanitizeMarkup(translation.result)
        .split(/\r?\n+/)
        .map((line) => normalizeText(line))
        .filter(Boolean)
    : []

  const showDetailsPanel = activePanel === 'details'
  const showImagePanel = activePanel === 'images'
  const hasDetailsPanelContent =
    (state === 'lookup' && Boolean(dictionary)) ||
    (state === 'translate' && Boolean(translation))
  const selectedText = cleanSelection || 'Selection'
  const images = imageCandidates(selectedText)

  return (
    <section className="apl-popover" data-testid="popover" role="dialog" aria-modal="true" aria-labelledby="apl-popover-title">
      <header className="apl-popover-header">
        <h2 id="apl-popover-title">{selectedText}</h2>
        <div className="apl-popover-tools" role="toolbar" aria-label="Popover tools">
          <button
            type="button"
            className="apl-popover-tool-btn"
            data-active={showDetailsPanel}
            onClick={() => togglePanel('details')}
          >
            Details
          </button>
          <button
            type="button"
            className="apl-popover-tool-btn"
            data-active={showImagePanel}
            onClick={() => togglePanel('images')}
          >
            Images
          </button>
          <button
            type="button"
            className="apl-popover-tool-btn"
            onClick={() => void playAudio()}
            disabled={!canPlayAudio}
          >
            {audioPlaying ? 'Stop Audio' : 'Audio'}
          </button>
          <button
            type="button"
            className="apl-popover-tool-btn apl-popover-tool-btn--settings"
            onClick={onOpenSettings}
          >
            Settings
          </button>
        </div>
      </header>

      {state === 'loading' && (
        <p className="apl-status" role="status" aria-live="polite">
          Loading...
        </p>
      )}

      {state === 'lookup' && dictionary && (
        <div className="apl-content apl-content--lookup">
          <p className="apl-lookup-word">{normalizeText(sanitizeMarkup(dictionary.word || cleanSelection))}</p>
          {dictionary.phonetic && <p className="apl-phonetic">/{normalizeText(sanitizeMarkup(dictionary.phonetic))}/</p>}
          {lookupSummary && (
            <button
              type="button"
              className="apl-summary-trigger"
              onClick={() => setActivePanel('details')}
            >
              {lookupSummary}
            </button>
          )}
          <p className="apl-meta">
            Provider: {dictionary.provider}
            {dictionary.fallback_used ? ' (fallback)' : ''}
          </p>
        </div>
      )}

      {state === 'translate' && translation && (
        <div className="apl-content apl-content--translate">
          {translationLines.length > 0 ? (
            translationLines.map((line, index) => (
              <p key={`${index}-${line}`} className="apl-translation">
                {line}
              </p>
            ))
          ) : (
            <p className="apl-translation">{normalizeText(sanitizeMarkup(translation.result))}</p>
          )}
          <p className="apl-meta">Engine: {translation.engine}</p>
        </div>
      )}

      {audioError && <p className="apl-error">{audioError}</p>}

      {state === 'error' && <p className="apl-error">{error ?? 'Unknown error'}</p>}

      {showDetailsPanel && hasDetailsPanelContent && (
        <aside className="apl-subpanel" data-panel-mode="details">
          {state === 'lookup' && dictionary && (
            <div className="apl-subpanel-body">
              {dictionary.meanings.map((meaning, meaningIndex) => (
                <article
                  key={`${meaning.part_of_speech}-${meaningIndex}`}
                  className="apl-meaning"
                >
                  <h3>{normalizeText(sanitizeMarkup(meaning.part_of_speech || 'Meaning'))}</h3>
                  <ul>
                    {meaning.definitions.map((definition, definitionIndex) => (
                      <li key={`${meaningIndex}-${definitionIndex}-${definition}`}>
                        {normalizeText(sanitizeMarkup(definition))}
                      </li>
                    ))}
                  </ul>
                  {meaning.example && <p className="apl-example">Example: {normalizeText(sanitizeMarkup(meaning.example))}</p>}
                </article>
              ))}
            </div>
          )}

          {state === 'translate' && translation && (
            <div className="apl-subpanel-body">
              <p className="apl-meta">Mode: {translation.mode}</p>
              <p className="apl-meta">Engine: {translation.engine}</p>
            </div>
          )}
        </aside>
      )}

      {showImagePanel && (
        <aside className="apl-subpanel" data-panel-mode="images">
          <div className="apl-subpanel-body apl-image-grid">
            {images.length > 0 ? images.map((src, index) => (
              <article key={`${src}-${index}`} className="apl-image-card">
                <img src={src} alt={`${selectedText} ${index + 1}`} loading="lazy" />
              </article>
            )) : (
              <p className="apl-meta">No image query.</p>
            )}
          </div>
        </aside>
      )}
    </section>
  )
}
