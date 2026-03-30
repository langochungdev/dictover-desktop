from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

try:
    from .translation import lookup_dictionary, translate
except ImportError:
    from translation import lookup_dictionary, translate


SUPPORTED_SOURCE_LANGS = {
    "auto",
    "vi",
    "en",
    "zh-CN",
    "ja",
    "ko",
    "ru",
    "de",
    "fr",
    "fi",
}
SUPPORTED_TARGET_LANGS = {"vi", "en", "zh-CN", "ja", "ko", "ru", "de", "fr", "fi"}


class TranslateRequest(BaseModel):
    text: str = Field(min_length=0)
    source: str = Field(default="auto")
    target: str = Field(default="en")

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in SUPPORTED_SOURCE_LANGS:
            raise ValueError("unsupported source language")
        return value

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        if value not in SUPPORTED_TARGET_LANGS:
            raise ValueError("unsupported target language")
        return value


class LookupRequest(BaseModel):
    word: str = Field(min_length=1)
    source_lang: str = Field(default="en")

    @field_validator("source_lang")
    @classmethod
    def validate_source_lang(cls, value: str) -> str:
        if value not in SUPPORTED_SOURCE_LANGS:
            raise ValueError("unsupported source language")
        return value


app = FastAPI(title="DictOver Sidecar", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/translate")
async def translate_endpoint(req: TranslateRequest) -> dict[str, str]:
    try:
        result = translate(req.text, req.source, req.target)
        return {
            "result": result.result,
            "engine": result.engine,
            "mode": result.mode,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/lookup")
async def lookup_endpoint(req: LookupRequest) -> dict:
    try:
        return lookup_dictionary(req.word, req.source_lang)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
