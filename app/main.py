from fastapi import FastAPI

from app.routers import products, sales, users

app = FastAPI(title="Commerce API", version="0.1.0")

app.include_router(users.router)
app.include_router(products.router)
app.include_router(sales.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
