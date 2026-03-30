import { useCallback, useState } from "react";
import { translateText, type TranslateResult } from "@/services/translate";

type TranslateStatus = "idle" | "loading" | "success" | "error";

interface UseTranslateState {
  status: TranslateStatus;
  result: TranslateResult | null;
  error: string | null;
}

const INITIAL_STATE: UseTranslateState = {
  status: "idle",
  result: null,
  error: null,
};

export function useTranslate() {
  const [state, setState] = useState<UseTranslateState>(INITIAL_STATE);

  const runTranslate = useCallback(
    async (text: string, source: string, target: string) => {
      setState({ status: "loading", result: null, error: null });
      try {
        const result = await translateText({ text, source, target });
        setState({ status: "success", result, error: null });
        return result;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Translate request failed";
        setState({ status: "error", result: null, error: message });
        throw error;
      }
    },
    [],
  );

  return {
    ...state,
    runTranslate,
  };
}
