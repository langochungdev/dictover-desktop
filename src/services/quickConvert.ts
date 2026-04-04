import { invoke } from "@tauri-apps/api/core";
import { sidecarPost } from "@/services/tauri";

export interface QuickConvertWordData {
  input: string;
  phonetic?: string | null;
  part_of_speech?: string | null;
  audio_url?: string | null;
  audio_lang?: string | null;
  synonyms: string[];
  related: string[];
  sounds_like: string[];
}

export interface QuickConvertResult {
  kind: "word" | "text";
  result: string;
  engine: string;
  mode: string;
  fallback_used: boolean;
  word_data: QuickConvertWordData | null;
}

export interface QuickConvertRequest {
  text: string;
  source: string;
  target: string;
}

export async function quickConvertText(
  request: QuickConvertRequest,
): Promise<QuickConvertResult> {
  const hasBridge =
    typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

  try {
    if (hasBridge) {
      return await invoke<QuickConvertResult>("quick_convert_text", {
        payload: request,
      });
    }

    return await sidecarPost<QuickConvertResult>("/quick-convert", request);
  } catch (fetchError) {
    const fetchMessage =
      fetchError instanceof Error ? fetchError.message : String(fetchError);
    console.error("[quick-convert] sidecar fetch failed", {
      source: request.source,
      target: request.target,
      textLength: request.text.length,
      endpoint: "http://127.0.0.1:49152/quick-convert",
      fetchError: fetchMessage,
      phase: hasBridge ? "invoke-failed" : "sidecar-fetch-no-bridge",
    });
    throw new Error(
      `quick-convert:${hasBridge ? "invoke-failed" : "sidecar-fetch-no-bridge"}:fetch=${fetchMessage}`,
    );
  }
}
