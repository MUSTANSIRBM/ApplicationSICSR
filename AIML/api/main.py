"""
api/main.py — the FastAPI app. Run from PROJECT ROOT (planner.db is a
relative path):
    uvicorn api.main:app --port 8000
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from planner.db import DB_FILE, create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Self-healing boot: fresh clone with no planner.db → seeded on
    # first start. Demo insurance.
    if not os.path.exists(DB_FILE):
        from planner.seed import seed
        seed()
    create_all()
    yield


app = FastAPI(title="Block Planner API", version="0.1.0", lifespan=lifespan)

# CORS: frontend dev origin. Tell me if their port isn't 3000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


