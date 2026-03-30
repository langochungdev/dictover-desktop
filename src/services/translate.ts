import { invokeWithFallback, sidecarPost } from "@/services/tauri";

export interface TranslateResult {
  result: string;
  engine: string;
  mode: string;
}

export interface TranslateRequest {
  text: string;
  source: string;
  target: string;
}

export async function translateText(
  request: TranslateRequest,
): Promise<TranslateResult> {
  return invokeWithFallback<TranslateResult>(
    "translate_text",
    { payload: request },
    async () => sidecarPost<TranslateResult>("/translate", request),
  );
}
