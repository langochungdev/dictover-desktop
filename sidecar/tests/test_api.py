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

    response = client.post("/translate", json={"text": "xin chào", "source": "vi", "target": "en"})
    assert response.status_code == 200
    assert response.json()["result"] == "Hello"


def test_translate_invalid_lang() -> None:
    response = client.post("/translate", json={"text": "test", "source": "xx", "target": "en"})
    assert response.status_code == 422


def test_lookup_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        sidecar_main,
        "lookup_dictionary",
        lambda word, source_lang: {
            "word": word,
            "phonetic": None,
            "audio_url": None,
            "meanings": [{"part_of_speech": "noun", "definitions": ["hello"], "example": None}],
            "provider": "test",
            "fallback_used": False,
        },
    )

    response = client.post("/lookup", json={"word": "xin chào", "source_lang": "vi"})
    assert response.status_code == 200
    body = response.json()
    assert body["word"] == "xin chào"
    assert body["provider"] == "test"
