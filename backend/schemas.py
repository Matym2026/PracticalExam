from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class ShortenRequest(BaseModel):
    original_url: str

    @field_validator("original_url")
    @classmethod
    def validar_url(cls, valor: str) -> str:
        valor = valor.strip()
        partes = urlparse(valor)
        if partes.scheme not in ("http", "https") or not partes.netloc:
            raise ValueError("La URL debe comenzar con http:// o https://")
        return valor


class ShortenResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str


class UrlInfo(BaseModel):
    short_code: str
    original_url: str
    created_at: str
