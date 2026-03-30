from __future__ import annotations

import sidecar.engines as engines
from sidecar.engines import TranslationResult


def test_translate_empty_string() -> None:
    result = engines.translate("", source="vi", target="en")
    assert result.result == ""
    assert result.mode == "empty"


def test_detect_language_known_cases(monkeypatch) -> None:
    monkeypatch.setattr(engines, "detect", lambda _: "en")
    assert engines.detect_language("The weather is beautiful today.") == "en"

    monkeypatch.setattr(engines, "detect", lambda _: "zh-cn")
    assert engines.detect_language("今天天气很好，我想出去走走。") == "zh-CN"


def test_detect_language_defaults_to_en_when_detector_missing(monkeypatch) -> None:
    monkeypatch.setattr(engines, "detect", None)
    assert engines.detect_language("xin chào") == "en"


def test_translate_prefers_argos(monkeypatch) -> None:
    class FakeArgos:
        def translate(self, text: str, source: str, target: str) -> TranslationResult:
            assert text == "xin chào"
            assert source == "vi"
            assert target == "en"
            return TranslationResult("hello", "argos", "direct")

    monkeypatch.setattr(engines, "ARGOS", FakeArgos())

    result = engines.translate("xin chào", source="vi", target="en")
    assert result.result == "hello"
    assert result.engine == "argos"


def test_translate_falls_back_api(monkeypatch) -> None:
    class BrokenArgos:
        def translate(self, text: str, source: str, target: str) -> TranslationResult:
            raise RuntimeError("argos failure")

    monkeypatch.setattr(engines, "ARGOS", BrokenArgos())
    monkeypatch.setattr(
        engines,
        "fallback_translate_api",
        lambda text, source, target: TranslationResult(
            "hello", "mymemory", "api-fallback"
        ),
    )

    result = engines.translate("xin chào", source="vi", target="en")
    assert result.result == "hello"
    assert result.engine == "mymemory"


def test_translate_auto_detect_source(monkeypatch) -> None:
    class CaptureArgos:
        called_with: tuple[str, str] | None = None

        def translate(self, text: str, source: str, target: str) -> TranslationResult:
            self.called_with = (source, target)
            return TranslationResult("hello", "argos", "direct")

    capture = CaptureArgos()
    monkeypatch.setattr(engines, "ARGOS", capture)
    monkeypatch.setattr(engines, "detect_language", lambda _: "vi")

    result = engines.translate("xin chào", source="auto", target="en")
    assert result.result == "hello"
    assert capture.called_with == ("vi", "en")


def test_argos_runtime_pivot_path() -> None:
    runtime = engines.ArgosRuntime.__new__(engines.ArgosRuntime)
    runtime.available = True
    runtime.error = None
    runtime._direct_pairs = {("vi", "en"), ("en", "ja")}

    class FakeTranslateModule:
        @staticmethod
        def translate(text: str, source: str, target: str) -> str:
            if source == "vi" and target == "en":
                return "hello"
            if source == "en" and target == "ja":
                return "こんにちは"
            raise RuntimeError("unexpected pair")

    runtime._translate_module = FakeTranslateModule()

    result = runtime.translate("xin chào", source="vi", target="ja")
    assert result.mode == "pivot"
    assert result.result == "こんにちは"
