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
  onClose: () => void
}

export function Popover({
  state,
  selection,
  dictionary,
  translation,
  error,
  panelMode,
  onClose
}: PopoverProps) {
  if (state === 'idle') {
    return null
  }

  return (
    <section className="apl-popover" data-testid="popover" role="dialog" aria-modal="true" aria-labelledby="apl-popover-title">
      <header className="apl-popover-header">
        <h2 id="apl-popover-title">{selection || 'Selection'}</h2>
        <button type="button" className="apl-close-btn" onClick={onClose}>
          Close
        </button>
      </header>

      {state === 'loading' && <p className="apl-status">Loading...</p>}

      {state === 'lookup' && dictionary && (
        <div className="apl-content">
          {dictionary.phonetic && <p className="apl-phonetic">/{dictionary.phonetic}/</p>}
          {dictionary.meanings.map((meaning) => (
            <article key={`${meaning.part_of_speech}-${meaning.definitions[0] ?? ''}`} className="apl-meaning">
              <h3>{meaning.part_of_speech || 'Meaning'}</h3>
              <ul>
                {meaning.definitions.map((definition) => (
                  <li key={definition}>{definition}</li>
                ))}
              </ul>
              {meaning.example && <p className="apl-example">Example: {meaning.example}</p>}
            </article>
          ))}
        </div>
      )}

      {state === 'translate' && translation && (
        <div className="apl-content">
          <p className="apl-translation">{translation.result}</p>
          <p className="apl-meta">Engine: {translation.engine}</p>
        </div>
      )}

      {state === 'error' && <p className="apl-error">{error ?? 'Unknown error'}</p>}

      {panelMode !== 'none' && <aside className="apl-subpanel">Panel: {panelMode}</aside>}
    </section>
  )
}
