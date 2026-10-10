
from fastapi import FastAPI

app = FastAPI(title="LAYOVER API")


@app.get("/")
def home():
    return {
        "message": "Welcome to LAYOVER!",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
