# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.data.database import create_db_and_tables
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down")


app = FastAPI(
    title="AI Block Planning System API",
    description="Railway maintenance scheduling API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes at BOTH paths for compatibility
app.include_router(router, prefix="/api/v1")  # Keep existing v1
app.include_router(router, prefix="/api")     # Add non-versioned path

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "message": "AI Block Planning System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "reference": "/api/reference",
            "defects": "/api/defects",
            "plan": "/api/plan",
            "solves": "/api/solves",
            "solve": "/api/solve (POST)",
            "impact": "/api/impact",
            "corridors": "/api/corridors"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)