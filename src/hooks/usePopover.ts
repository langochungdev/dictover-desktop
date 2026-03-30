import { useCallback, useState } from 'react'
import { lookupDictionary, type DictionaryResult } from '@/services/dictionary'
import { translateText, type TranslateResult } from '@/services/translate'
import type { AppSettings } from '@/types/settings'

export type PopoverState = 'idle' | 'loading' | 'lookup' | 'translate' | 'error'
export type PopoverTrigger = 'auto' | 'shortcut'

export interface PopoverData {
  selectedText: string
  dictionary: DictionaryResult | null
  translation: TranslateResult | null
}

const EMPTY_DATA: PopoverData = {
  selectedText: '',
  dictionary: null,
  translation: null
}

function countWords(input: string): number {
  const words = input.trim().split(/\s+/).filter(Boolean)
  return words.length
}

export function getActionType(input: string): 'lookup' | 'translate' {
  return countWords(input) === 1 ? 'lookup' : 'translate'
}

export function usePopover(settings: AppSettings) {
  const [state, setState] = useState<PopoverState>('idle')
  const [data, setData] = useState<PopoverData>(EMPTY_DATA)
  const [error, setError] = useState<string | null>(null)

  const close = useCallback(() => {
    setState('idle')
    setData(EMPTY_DATA)
    setError(null)
  }, [])

  const openFromSelection = useCallback(
    async (rawText: string, trigger: PopoverTrigger) => {
      const selectedText = rawText.trim()
      if (!selectedText) {
        close()
        return
      }
      if (settings.popover_trigger_mode === 'shortcut' && trigger !== 'shortcut') {
        return
      }
      setState('loading')
      setError(null)
      const nextData: PopoverData = {
        selectedText,
        dictionary: null,
        translation: null
      }
      try {
        const actionType = getActionType(selectedText)
        if (actionType === 'lookup' && settings.enable_lookup) {
          const source = settings.source_language === 'auto' ? 'en' : settings.source_language
          const dictionary = await lookupDictionary({ word: selectedText, source_lang: source })
          nextData.dictionary = {
            ...dictionary,
            meanings: dictionary.meanings.slice(0, settings.max_definitions)
          }
          setData(nextData)
          setState('lookup')
          return
        }
        if (settings.enable_translate) {
          const translation = await translateText({
            text: selectedText,
            source: settings.source_language,
            target: settings.target_language
          })
          nextData.translation = translation
          setData(nextData)
          setState('translate')
          return
        }
        setData(nextData)
        setState('idle')
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : 'Popover request failed'
        setData(nextData)
        setError(message)
        setState('error')
      }
    },
    [close, settings]
  )

  return {
    state,
    data,
    error,
    close,
    openFromSelection
  }
}
