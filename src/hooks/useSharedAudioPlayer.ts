import { useCallback, useEffect, useRef, useState } from "react";
import { appendDebugLog } from "@/services/debugLog";
import { sidecarUrl } from "@/services/tauri";
import {
  buildAlternativeAudioUrl,
  normalizeText,
} from "@/components/Popover/popover.utils";

interface SharedAudioPlayerOptions {
  audioUrl?: string | null;
  fallbackWord?: string | null;
  fallbackLang?: string | null;
  debugScope?: string;
}

function hostOf(url: string): string {
  try {
    return new URL(url).host.toLowerCase();
  } catch {
    return "invalid-url";
  }
}

function isGoogleTtsHost(host: string): boolean {
  return host === "translate.google.com" || host === "translate.googleapis.com";
}

function withProxyIfGoogle(url: string): string | null {
  const host = hostOf(url);
  if (!isGoogleTtsHost(host)) {
    return null;
  }
  return sidecarUrl(`/tts-proxy?url=${encodeURIComponent(url)}`);
}

export function useSharedAudioPlayer({
  audioUrl,
  fallbackWord,
  fallbackLang,
  debugScope,
}: SharedAudioPlayerOptions) {
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playAttemptInFlightRef = useRef(false);

  const log = useCallback(
    (title: string, detail: string) => {
      if (!debugScope) {
        return;
      }
      appendDebugLog(debugScope, title, detail);
    },
    [debugScope],
  );

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setAudioPlaying(false);
  }, []);

  useEffect(
    () => () => {
      stopAudio();
    },
    [stopAudio],
  );

  const startAudio = useCallback(async () => {
    if (playAttemptInFlightRef.current) {
      log("Audio playback skipped", "reason=in-flight-attempt");
      return;
    }
    playAttemptInFlightRef.current = true;

    try {
      setAudioError(null);
      stopAudio();

      const source = String(audioUrl || "").trim();
      const fallbackText = normalizeText(fallbackWord || "");
      const fallbackLanguage = normalizeText(fallbackLang || "en");

    const tryPlayUrl = async (url: string): Promise<boolean> => {
      if (!url) {
        return false;
      }
      const host = hostOf(url);

      try {
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => setAudioPlaying(false);
        audio.onerror = () => setAudioPlaying(false);
        setAudioPlaying(true);
        await audio.play();
        log("Audio url playback", `ok=1 host=${host} mode=direct`);
        return true;
      } catch (error) {
        setAudioPlaying(false);
        log(
          "Audio url playback",
          `ok=0 host=${host} mode=direct error=${error instanceof Error ? error.message : String(error)}`,
        );
        return false;
      }
    };

      const candidates: string[] = [];
      if (source) {
        const proxied = withProxyIfGoogle(source);
        if (proxied) {
          candidates.push(proxied);
        }
        candidates.push(source);

        const alt = buildAlternativeAudioUrl(source);
        if (alt) {
          const proxiedAlt = withProxyIfGoogle(alt);
          if (proxiedAlt) {
            candidates.push(proxiedAlt);
          }
          candidates.push(alt);
        }
      }

      const uniqueCandidates: string[] = [];
      const seen = new Set<string>();
      for (const candidate of candidates) {
        const normalized = candidate.trim();
        if (!normalized || seen.has(normalized)) {
          continue;
        }
        seen.add(normalized);
        uniqueCandidates.push(normalized);
      }

      for (const candidate of uniqueCandidates) {
        if (await tryPlayUrl(candidate)) {
          return;
        }
      }

      if (
        fallbackText &&
        typeof window !== "undefined" &&
        window.speechSynthesis
      ) {
        const voices = window.speechSynthesis.getVoices();
        const preferred = fallbackLanguage.toLowerCase();
        const hasPreferredVoice = preferred
          ? voices.some((voice) => voice.lang.toLowerCase().startsWith(preferred))
          : false;
        const resolvedLang = hasPreferredVoice ? fallbackLanguage : "";

        const utterance = new SpeechSynthesisUtterance(fallbackText);
        if (resolvedLang) {
          utterance.lang = resolvedLang;
        }
        utterance.onstart = () => setAudioPlaying(true);
        utterance.onend = () => setAudioPlaying(false);
        utterance.onerror = () => {
          setAudioPlaying(false);
          setAudioError("Audio playback failed");
        };
        window.speechSynthesis.speak(utterance);
        log(
          "Audio speech fallback",
          `lang=${resolvedLang || "default"} requested=${fallbackLanguage || "unknown"} voices=${voices.length} textLen=${fallbackText.length}`,
        );
        return;
      }

      setAudioError("Audio playback failed");
      log(
        "Audio playback failed",
        `hasSource=${source ? 1 : 0} hasFallbackWord=${fallbackText ? 1 : 0}`,
      );
    } finally {
      playAttemptInFlightRef.current = false;
    }
  }, [audioUrl, fallbackLang, fallbackWord, log, stopAudio]);

  const playAudio = useCallback(() => {
    if (audioPlaying) {
      stopAudio();
      return;
    }
    void startAudio();
  }, [audioPlaying, startAudio, stopAudio]);

  return { audioPlaying, audioError, playAudio, startAudio, stopAudio };
}
