import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import products, sales, users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API starting")
    yield
    logger.info("API shutting down")


app = FastAPI(title="Commerce API", version="0.1.0", lifespan=lifespan)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(sales.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
