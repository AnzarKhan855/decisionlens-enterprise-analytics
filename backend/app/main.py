from fastapi import FastAPI

from app.api.v1.routes import api_router

app = FastAPI(
    title="DecisionLens Enterprise Analytics Platform",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def home():
    return {
        "message": "DecisionLens Enterprise Analytics Platform"
    }