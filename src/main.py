from fastapi import FastAPI

from src.modules.health.controller import router as health_router

app = FastAPI()

app.include_router(health_router)


@app.get("/")
def root():
    return {"message": "Pizzaria API"}