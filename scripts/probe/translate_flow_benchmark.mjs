import { performance } from "node:perf_hooks";
import fs from "node:fs/promises";

const SIDECAR_BASE = process.env.SIDECAR_BASE || "http://127.0.0.1:49152";

const SUPPORTED_LANGS = ["vi", "en", "zh-CN", "ja", "ko", "ru", "de", "fr", "fi"];

const SAMPLE_TEXTS = {
  vi: "Xin chao, toi dang thu nghiem chat luong dich thuat hom nay.",
  en: "Hello, I am testing translation quality and speed today.",
  "zh-CN": "你好，我今天在测试翻译质量和速度。",
  ja: "こんにちは、今日は翻訳の品質と速度をテストしています。",
  ko: "안녕하세요, 오늘 번역 품질과 속도를 테스트하고 있습니다.",
  ru: "Привет, сегодня я тестирую качество и скорость перевода.",
  de: "Hallo, ich teste heute die Qualitat und Geschwindigkeit der Ubersetzung.",
  fr: "Bonjour, je teste aujourd'hui la qualite et la vitesse de traduction.",
  fi: "Hei, testaan tanaan kaannoksen laatua ja nopeutta.",
};

const AUTO_PROBES = [
  "Xin chao, hom nay toi muon test auto detect.",
  "こんにちは、これは自動言語判定のテストです。",
  "Hello, this is an auto detection test for translation flow.",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N}]+/gu, "")
    .trim();
}

function ngramSet(value, n = 2) {
  const normalized = normalizeText(value);
  if (!normalized) {
    return new Set();
  }
  if (normalized.length <= n) {
    return new Set([normalized]);
  }
  const grams = new Set();
  for (let i = 0; i <= normalized.length - n; i += 1) {
    grams.add(normalized.slice(i, i + n));
  }
  return grams;
}

function diceSimilarity(a, b) {
  const setA = ngramSet(a, 2);
  const setB = ngramSet(b, 2);
  if (!setA.size || !setB.size) {
    return 0;
  }
  let overlap = 0;
  for (const item of setA) {
    if (setB.has(item)) {
      overlap += 1;
    }
  }
  return (2 * overlap) / (setA.size + setB.size);
}

function scriptMatchRatio(text, targetLang) {
  const s = String(text || "");
  if (!s.trim()) {
    return 0;
  }

  const chars = [...s];
  const letters = chars.filter((ch) => /\p{L}/u.test(ch));
  if (!letters.length) {
    return 0;
  }

  const countMatches = (regex) => letters.filter((ch) => regex.test(ch)).length;

  if (targetLang === "ru") {
    return countMatches(/[\p{Script=Cyrillic}]/u) / letters.length;
  }

  if (targetLang === "ko") {
    return countMatches(/[\p{Script=Hangul}]/u) / letters.length;
  }

  if (targetLang === "ja") {
    return countMatches(/[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u) / letters.length;
  }

  if (targetLang === "zh-CN") {
    return countMatches(/[\p{Script=Han}]/u) / letters.length;
  }

  return countMatches(/[\p{Script=Latin}]/u) / letters.length;
}

function qualityScore(input, output, backTranslated, sourceLang, targetLang) {
  const outputText = String(output || "").trim();
  const inputText = String(input || "").trim();

  const hasOutput = outputText.length > 0 ? 1 : 0;
  const changed = normalizeText(inputText) !== normalizeText(outputText) ? 1 : 0;
  const lengthRatio = inputText.length > 0 ? outputText.length / inputText.length : 0;
  const lengthRatioOk = lengthRatio >= 0.35 && lengthRatio <= 3.2 ? 1 : 0;
  const scriptRatio = scriptMatchRatio(outputText, targetLang);
  const roundTrip = diceSimilarity(inputText, backTranslated || "");

  const score =
    hasOutput * 30 +
    scriptRatio * 25 +
    roundTrip * 35 +
    lengthRatioOk * 10;

  return {
    score: Number(score.toFixed(2)),
    changed,
    lengthRatio: Number(lengthRatio.toFixed(3)),
    scriptRatio: Number(scriptRatio.toFixed(3)),
    roundTrip: Number(roundTrip.toFixed(3)),
    sourceLang,
    targetLang,
  };
}

async function fetchJson(url, options = {}, timeoutMs = 18000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const started = performance.now();
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    const elapsedMs = performance.now() - started;
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }

    return {
      ok: response.ok,
      status: response.status,
      elapsedMs,
      text,
      json,
    };
  } catch (error) {
    const elapsedMs = performance.now() - started;
    return {
      ok: false,
      status: 0,
      elapsedMs,
      text: "",
      json: null,
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timer);
  }
}

async function sidecarTranslate(text, source, target) {
  const result = await fetchJson(
    `${SIDECAR_BASE}/translate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source, target }),
    },
    25000,
  );

  return {
    ok: result.ok,
    elapsedMs: Number(result.elapsedMs.toFixed(2)),
    result: result.json?.result || "",
    engine: result.json?.engine || null,
    mode: result.json?.mode || null,
    status: result.status,
    error: result.error || (!result.ok ? result.text.slice(0, 200) : null),
    route: "sidecar",
  };
}

function googleLang(code) {
  if (code === "zh-CN") {
    return "zh-CN";
  }
  return code;
}

function parseGoogleResult(payload) {
  if (!Array.isArray(payload) || !Array.isArray(payload[0])) {
    return "";
  }
  return payload[0]
    .map((chunk) => (Array.isArray(chunk) ? String(chunk[0] || "") : ""))
    .join("")
    .trim();
}

async function googleUnofficialTranslate(text, source, target) {
  const sl = source === "auto" ? "auto" : googleLang(source);
  const tl = googleLang(target);
  const query = new URLSearchParams({
    client: "gtx",
    sl,
    tl,
    dt: "t",
    q: text,
  });

  const result = await fetchJson(
    `https://translate.googleapis.com/translate_a/single?${query.toString()}`,
    { method: "GET" },
    18000,
  );

  const translated = parseGoogleResult(result.json);

  return {
    ok: result.ok && translated.length > 0,
    elapsedMs: Number(result.elapsedMs.toFixed(2)),
    result: translated,
    engine: "google-unofficial",
    mode: "api-main",
    status: result.status,
    error: result.error || (!result.ok ? result.text.slice(0, 200) : null),
    route: "google-unofficial",
  };
}

async function googlePrimaryFlow(text, source, target) {
  const main = await googleUnofficialTranslate(text, source, target);
  if (main.ok) {
    return main;
  }

  const fallback = await sidecarTranslate(text, source, target);
  return {
    ...fallback,
    route: "google-fallback-sidecar",
    fallbackFromGoogle: true,
    googleError: main.error,
  };
}

function summarize(records) {
  const okRecords = records.filter((r) => r.ok);
  const avgLatency = okRecords.length
    ? okRecords.reduce((sum, r) => sum + r.elapsedMs, 0) / okRecords.length
    : 0;
  const p95Latency = okRecords.length
    ? [...okRecords]
        .sort((a, b) => a.elapsedMs - b.elapsedMs)[Math.floor(okRecords.length * 0.95) - 1 >= 0 ? Math.floor(okRecords.length * 0.95) - 1 : 0]
        ?.elapsedMs || 0
    : 0;

  const avgQuality = okRecords.length
    ? okRecords.reduce((sum, r) => sum + (r.quality?.score || 0), 0) / okRecords.length
    : 0;

  return {
    total: records.length,
    ok: okRecords.length,
    fail: records.length - okRecords.length,
    successRate: records.length ? Number(((okRecords.length / records.length) * 100).toFixed(2)) : 0,
    avgLatencyMs: Number(avgLatency.toFixed(2)),
    p95LatencyMs: Number(p95Latency.toFixed(2)),
    avgQualityScore: Number(avgQuality.toFixed(2)),
  };
}

async function waitForSidecarHealth() {
  for (let i = 0; i < 25; i += 1) {
    const health = await fetchJson(`${SIDECAR_BASE}/health`, { method: "GET" }, 2500);
    if (health.ok) {
      return true;
    }
    await sleep(300);
  }
  return false;
}

function buildCases() {
  const cases = [];
  for (const source of SUPPORTED_LANGS) {
    const text = SAMPLE_TEXTS[source];
    for (const target of SUPPORTED_LANGS) {
      if (target === source) {
        continue;
      }
      cases.push({
        id: `${source}->${target}`,
        source,
        target,
        text,
        group: "matrix",
      });
    }
  }

  for (const [index, probe] of AUTO_PROBES.entries()) {
    for (const target of SUPPORTED_LANGS) {
      cases.push({
        id: `auto-${index + 1}->${target}`,
        source: "auto",
        target,
        text: probe,
        group: "auto",
      });
    }
  }

  return cases;
}

async function run() {
  const healthy = await waitForSidecarHealth();
  if (!healthy) {
    throw new Error(`sidecar health check failed at ${SIDECAR_BASE}`);
  }

  const cases = buildCases();
  const currentFlowRecords = [];
  const googlePrimaryRecords = [];

  for (const testCase of cases) {
    const current = await sidecarTranslate(testCase.text, testCase.source, testCase.target);
    let currentBackText = "";
    if (current.ok) {
      const currentBack = await sidecarTranslate(current.result, testCase.target, testCase.source === "auto" ? "en" : testCase.source);
      currentBackText = currentBack.ok ? currentBack.result : "";
    }
    const currentQuality = qualityScore(
      testCase.text,
      current.result,
      currentBackText,
      testCase.source,
      testCase.target,
    );

    currentFlowRecords.push({
      ...testCase,
      flow: "current",
      ...current,
      backTranslated: currentBackText,
      quality: currentQuality,
    });

    const googlePrimary = await googlePrimaryFlow(testCase.text, testCase.source, testCase.target);
    let googleBackText = "";
    if (googlePrimary.ok) {
      const back = await googleUnofficialTranslate(
        googlePrimary.result,
        testCase.target,
        testCase.source === "auto" ? "en" : testCase.source,
      );
      googleBackText = back.ok ? back.result : "";
    }

    const googleQuality = qualityScore(
      testCase.text,
      googlePrimary.result,
      googleBackText,
      testCase.source,
      testCase.target,
    );

    googlePrimaryRecords.push({
      ...testCase,
      flow: "google-primary",
      ...googlePrimary,
      backTranslated: googleBackText,
      quality: googleQuality,
    });
  }

  const currentSummary = summarize(currentFlowRecords);
  const googleSummary = summarize(googlePrimaryRecords);

  const currentEngineStats = currentFlowRecords.reduce((acc, item) => {
    const key = item.engine || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const currentModeStats = currentFlowRecords.reduce((acc, item) => {
    const key = item.mode || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const googleRouteStats = googlePrimaryRecords.reduce((acc, item) => {
    const key = item.route || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const output = {
    generatedAt: new Date().toISOString(),
    sidecarBase: SIDECAR_BASE,
    coverage: {
      matrixPairs: SUPPORTED_LANGS.length * (SUPPORTED_LANGS.length - 1),
      autoCases: AUTO_PROBES.length * SUPPORTED_LANGS.length,
      totalCases: cases.length,
      supportedTargets: SUPPORTED_LANGS,
      supportedSources: ["auto", ...SUPPORTED_LANGS],
    },
    summaries: {
      currentFlow: currentSummary,
      googlePrimaryFlow: googleSummary,
    },
    currentFlowStats: {
      engine: currentEngineStats,
      mode: currentModeStats,
    },
    googlePrimaryStats: {
      route: googleRouteStats,
    },
    records: {
      currentFlow: currentFlowRecords,
      googlePrimaryFlow: googlePrimaryRecords,
    },
  };

  await fs.mkdir("docs/results", { recursive: true });
  await fs.writeFile("docs/results/translate_flow_benchmark.json", JSON.stringify(output, null, 2));

  const lines = [
    "=== BENCHMARK COMPLETE ===",
    `Cases: ${cases.length}`,
    `Current flow success: ${currentSummary.successRate}% | avg ${currentSummary.avgLatencyMs}ms | p95 ${currentSummary.p95LatencyMs}ms | quality ${currentSummary.avgQualityScore}`,
    `Google-primary success: ${googleSummary.successRate}% | avg ${googleSummary.avgLatencyMs}ms | p95 ${googleSummary.p95LatencyMs}ms | quality ${googleSummary.avgQualityScore}`,
    `Current engines: ${JSON.stringify(currentEngineStats)}`,
    `Current modes: ${JSON.stringify(currentModeStats)}`,
    `Google routes: ${JSON.stringify(googleRouteStats)}`,
    "Saved: docs/results/translate_flow_benchmark.json",
  ];

  console.log(lines.join("\n"));
}

run().catch((error) => {
  console.error("Benchmark failed:", error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
