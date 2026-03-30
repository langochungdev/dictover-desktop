from __future__ import annotations

from fastapi.testclient import TestClient

import sidecar.main as sidecar_main
from sidecar.engines import TranslationResult


client = TestClient(sidecar_main.app)


def test_translate_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        sidecar_main,
        "translate",
        lambda text, source, target: TranslationResult("Hello", "argos", "direct"),
    )

    response = client.post(
        "/translate", json={"text": "xin chào", "source": "vi", "target": "en"}
    )
    assert response.status_code == 200
    assert response.json()["result"] == "Hello"


def test_translate_invalid_lang() -> None:
    response = client.post(
        "/translate", json={"text": "test", "source": "xx", "target": "en"}
    )
    assert response.status_code == 422


def test_translate_endpoint_returns_500_when_translate_crashes(monkeypatch) -> None:
    def failing_translate(text: str, source: str, target: str) -> TranslationResult:
        del text, source, target
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(sidecar_main, "translate", failing_translate)

    response = client.post(
        "/translate", json={"text": "xin chào", "source": "vi", "target": "en"}
    )
    assert response.status_code == 500
    assert "engine exploded" in response.json()["detail"]


def test_lookup_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        sidecar_main,
        "lookup_dictionary",
        lambda word, source_lang: {
            "word": word,
            "phonetic": None,
            "audio_url": None,
            "meanings": [
                {"part_of_speech": "noun", "definitions": ["hello"], "example": None}
            ],
            "provider": "test",
            "fallback_used": False,
        },
    )

    response = client.post("/lookup", json={"word": "xin chào", "source_lang": "vi"})
    assert response.status_code == 200
    body = response.json()
    assert body["word"] == "xin chào"
    assert body["provider"] == "test"


def test_lookup_endpoint_returns_500_when_lookup_crashes(monkeypatch) -> None:
    def failing_lookup(word: str, source_lang: str) -> dict:
        del word, source_lang
        raise RuntimeError("lookup failed")

    monkeypatch.setattr(sidecar_main, "lookup_dictionary", failing_lookup)

    response = client.post("/lookup", json={"word": "xin chào", "source_lang": "vi"})
    assert response.status_code == 500
    assert "lookup failed" in response.json()["detail"]


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
