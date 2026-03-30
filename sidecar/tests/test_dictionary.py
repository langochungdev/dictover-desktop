from __future__ import annotations

from typing import Any

import sidecar.dictionary as dictionary


class FakeResponse:
    def __init__(self, ok: bool, payload: Any) -> None:
        self.ok = ok
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_lookup_non_english_uses_en_wiktionary_fallback(monkeypatch) -> None:
    calls: list[str] = []
    payload = {
        "en": [
            {
                "partOfSpeech": "noun",
                "definitions": [{"definition": "hello", "example": "hello there"}],
            }
        ]
    }

    def fake_get(url: str, timeout: int) -> FakeResponse:
        del timeout
        calls.append(url)
        if "vi.wiktionary.org" in url:
            return FakeResponse(False, {})
        return FakeResponse(True, payload)

    monkeypatch.setattr(dictionary.SESSION, "get", fake_get)

    result = dictionary.lookup_dictionary("xin chào", "vi")

    assert result["provider"] == "wiktionary-rest"
    assert result["fallback_used"] is True
    assert result["meanings"][0]["definitions"][0] == "hello"
    assert len(calls) == 2


def test_lookup_non_english_falls_back_to_translation(monkeypatch) -> None:
    monkeypatch.setattr(
        dictionary.SESSION, "get", lambda url, timeout: FakeResponse(False, {})
    )
    monkeypatch.setattr(
        dictionary,
        "translate",
        lambda text, source, target: type(
            "Result",
            (),
            {"result": f"{text}-{source}-{target}"},
        )(),
    )

    result = dictionary.lookup_dictionary("xin chào", "vi")

    assert result["provider"] == "auto_lookup_fallback"
    assert result["fallback_used"] is True
    assert result["meanings"][0]["definitions"] == ["xin chào-vi-en"]


def test_lookup_english_uses_dictionary_api(monkeypatch) -> None:
    payload = [
        {
            "phonetic": "həˈləʊ",
            "phonetics": [{"audio": "https://audio.example/hello.mp3"}],
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [
                        {"definition": "A greeting", "example": "Hello John"}
                    ],
                }
            ],
        }
    ]

    monkeypatch.setattr(
        dictionary.SESSION, "get", lambda url, timeout: FakeResponse(True, payload)
    )

    result = dictionary.lookup_dictionary("hello", "en")

    assert result["provider"] == "dictionaryapi.dev"
    assert result["fallback_used"] is False
    assert result["phonetic"] == "həˈləʊ"
    assert result["audio_url"] == "https://audio.example/hello.mp3"
