import { invokeWithFallback, sidecarPost } from "@/services/tauri";

export interface DictionaryMeaning {
  part_of_speech: string;
  definitions: string[];
  example: string | null;
}

export interface DictionaryResult {
  word: string;
  phonetic: string | null;
  audio_url: string | null;
  audio_lang?: string | null;
  meanings: DictionaryMeaning[];
  provider: string;
  fallback_used: boolean;
}

export interface DictionaryRequest {
  word: string;
  source_lang: string;
}

export async function lookupDictionary(
  request: DictionaryRequest,
): Promise<DictionaryResult> {
  return invokeWithFallback<DictionaryResult>(
    "lookup_dictionary",
    { payload: request },
    async () => sidecarPost<DictionaryResult>("/lookup", request),
  );
}
