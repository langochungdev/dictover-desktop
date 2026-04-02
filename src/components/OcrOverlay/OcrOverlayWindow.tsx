import { useEffect, useMemo, useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { appendDebugLog } from '@/services/debugLog'
import { loadSettings } from '@/services/config'
import type { OutputLanguageCode } from '@/constants/languages'
import type { AppSettings } from '@/types/settings'

const OCR_OVERLAY_HINTS: Record<OutputLanguageCode, string> = {
  vi: 'Kéo chuột để chọn vùng ảnh - Esc để hủy',
  en: 'Drag to select image area - Esc to cancel',
  'zh-CN': '拖动鼠标选择图像区域 - Esc 取消',
  ja: 'ドラッグして画像範囲を選択 - Escでキャンセル',
  ko: '드래그하여 이미지 영역 선택 - Esc로 취소',
  ru: 'Перетащите мышь, чтобы выбрать область изображения - Esc для отмены',
  de: 'Ziehen, um den Bildbereich auszuwählen - Esc zum Abbrechen',
  fr: 'Faites glisser pour sélectionner la zone d\'image - Échap pour annuler',
  fi: 'Valitse kuva-alue vetämällä - Esc peruuttaa',
}

interface DragPoint {
  viewX: number
  viewY: number
}

interface NormalizedRect {
  left: number
  top: number
  width: number
  height: number
}

type SettingsUpdatedPayload = Partial<AppSettings>

function resolveHintText(targetLanguage: OutputLanguageCode | undefined): string {
  if (!targetLanguage) {
    return OCR_OVERLAY_HINTS.en
  }
  return OCR_OVERLAY_HINTS[targetLanguage] ?? OCR_OVERLAY_HINTS.en
}

function normalizeRect(start: DragPoint, current: DragPoint): NormalizedRect {
  const viewLeft = Math.min(start.viewX, current.viewX)
  const viewTop = Math.min(start.viewY, current.viewY)
  const viewRight = Math.max(start.viewX, current.viewX)
  const viewBottom = Math.max(start.viewY, current.viewY)

  return {
    left: viewLeft,
    top: viewTop,
    width: viewRight - viewLeft,
    height: viewBottom - viewTop,
  }
}

function pointFromPointer(event: React.PointerEvent<HTMLElement>): DragPoint {
  return {
    viewX: event.clientX,
    viewY: event.clientY,
  }
}

export function OcrOverlayWindow() {
  const [start, setStart] = useState<DragPoint | null>(null)
  const [current, setCurrent] = useState<DragPoint | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [hintText, setHintText] = useState<string>(OCR_OVERLAY_HINTS.en)

  useEffect(() => {
    let mounted = true
    let cleanupSettingsUpdated: (() => void) | null = null

    void (async () => {
      try {
        const settings = await loadSettings()
        const next = resolveHintText(settings.target_language)
        if (mounted) {
          setHintText(next)
        }
      } catch {
        if (mounted) {
          setHintText(OCR_OVERLAY_HINTS.en)
        }
      }
    })()

    void (async () => {
      try {
        const unlisten = await listen<SettingsUpdatedPayload>('settings-updated', (event) => {
          if (!mounted) {
            return
          }
          const next = resolveHintText(event.payload.target_language)
          setHintText(next)
        })
        cleanupSettingsUpdated = unlisten
      } catch {
        cleanupSettingsUpdated = null
      }
    })()

    return () => {
      mounted = false
      cleanupSettingsUpdated?.()
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        void invoke('cancel_ocr_overlay').catch(() => undefined)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  const selection = useMemo(() => {
    if (!start || !current) {
      return null
    }
    return normalizeRect(start, current)
  }, [current, start])

  const handlePointerDown = (event: React.PointerEvent<HTMLElement>) => {
    if (submitting || event.button !== 0) {
      return
    }

    const point = pointFromPointer(event)
    setStart(point)
    setCurrent(point)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLElement>) => {
    if (!start || submitting) {
      return
    }

    setCurrent(pointFromPointer(event))
  }

  const handlePointerUp = (event: React.PointerEvent<HTMLElement>) => {
    if (!start || submitting) {
      return
    }

    const point = pointFromPointer(event)
    const rect = normalizeRect(start, point)
    setStart(null)
    setCurrent(null)

    if (rect.width < 8 || rect.height < 8) {
      appendDebugLog('trace', 'OCR selection canceled', 'region too small')
      void invoke('cancel_ocr_overlay').catch(() => undefined)
      return
    }

    setSubmitting(true)
    appendDebugLog(
      'trace',
      'OCR selection submit',
      `viewRect=(${Math.round(rect.left)},${Math.round(rect.top)},${Math.round(rect.width)},${Math.round(rect.height)})`,
    )
    void (async () => {
      try {
        await invoke('submit_ocr_selection', {
          left: Math.round(rect.left),
          top: Math.round(rect.top),
          right: Math.round(rect.left + rect.width),
          bottom: Math.round(rect.top + rect.height),
        })
        appendDebugLog('trace', 'OCR selection submit done')
      } catch {
        appendDebugLog('trace', 'OCR selection submit failed')
        await invoke('cancel_ocr_overlay').catch(() => undefined)
      } finally {
        setSubmitting(false)
      }
    })()
  }

  const handleContextMenu = (event: React.MouseEvent<HTMLElement>) => {
    event.preventDefault()
    if (!submitting) {
      void invoke('cancel_ocr_overlay').catch(() => undefined)
    }
  }

  return (
    <main
      className="apl-ocr-overlay-shell"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onContextMenu={handleContextMenu}
    >
      <div className="apl-ocr-overlay-hint">{hintText}</div>
      {selection && (
        <div
          className="apl-ocr-overlay-selection"
          style={{
            left: `${selection.left}px`,
            top: `${selection.top}px`,
            width: `${selection.width}px`,
            height: `${selection.height}px`,
          }}
        />
      )}
    </main>
  )
}
