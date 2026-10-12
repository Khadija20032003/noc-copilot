"""NOC Copilot API entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import missing_key_handler, router
from .llm import MissingAPIKeyError
from .tools.network_data import ensure_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database()  # generate the synthetic drive-test data on first start
    yield


app = FastAPI(title="NOC Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.add_exception_handler(MissingAPIKeyError, missing_key_handler)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
