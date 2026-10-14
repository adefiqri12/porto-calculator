"""FastAPI application factory."""
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import router

WEB_DIR = pathlib.Path(__file__).resolve().parent.parent / "web"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Porto Calculator",
        description="Offline calculator for investing and trading math.",
        version="0.1.0",
    )
    app.include_router(router)
    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
    return app
