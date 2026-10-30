import os
import uuid

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import database
from schemas import ShortenRequest, ShortenResponse, UrlInfo

# Ejemplo: http://<ip-publica-ec2>:8000
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
# Origen(es) del frontend en S3, separados por coma
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app = FastAPI(title="AWS URL Shortener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _es_uuid(valor: str) -> bool:
    try:
        uuid.UUID(valor)
        return True
    except ValueError:
        return False


@app.get("/health")
def health():
    return {"status": "ok"}


# Endpoint 1: crear enlace corto
@app.post("/shorten", response_model=ShortenResponse)
def shorten(datos: ShortenRequest):
    short_code = str(uuid.uuid4())  # El UUID se genera solo en el backend
    try:
        database.guardar_url(short_code, datos.original_url)
    except (BotoCoreError, ClientError):
        raise HTTPException(status_code=500, detail="No se pudo guardar en DynamoDB")
    return ShortenResponse(
        short_code=short_code,
        original_url=datos.original_url,
        short_url=f"{PUBLIC_BASE_URL}/{short_code}",
    )


# Endpoint 3: consultar informacion de un enlace
@app.get("/urls/{short_code}", response_model=UrlInfo)
def info(short_code: str):
    if not _es_uuid(short_code):
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    try:
        item = database.obtener_url(short_code)
    except (BotoCoreError, ClientError):
        raise HTTPException(status_code=500, detail="Error consultando DynamoDB")
    if not item:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    return UrlInfo(**item)


# Endpoint 2: redireccion (debe ir al final por ser una ruta generica)
@app.get("/{short_code}")
def redirect(short_code: str):
    if not _es_uuid(short_code):
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    try:
        item = database.obtener_url(short_code)
    except (BotoCoreError, ClientError):
        raise HTTPException(status_code=500, detail="Error consultando DynamoDB")
    if not item:
        raise HTTPException(status_code=404, detail="Enlace no encontrado")
    return RedirectResponse(url=item["original_url"], status_code=307)
