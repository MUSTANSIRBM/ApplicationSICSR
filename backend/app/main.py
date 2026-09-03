from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="The Flow API",
    description="Railway Block Planning System",
    version="0.1.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🚂 The Flow API is running!",
        "status": "healthy"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "the-flow-backend"}

@app.get("/api/defects")
async def get_defects():
    """Get all defects (mock data for now)"""
    return {
        "defects": [
            {"id": 1, "department": "Track", "severity": "High", "description": "Crack in rail at KM 45"},
            {"id": 2, "department": "Power", "severity": "Critical", "description": "Overhead wire damage"},
            {"id": 3, "department": "Signals", "severity": "Medium", "description": "Signal light malfunction"}
        ]
    }
