import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import navigator, crowd, volunteer, sustainability

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stadiumiq.main")

# Initialize FastAPI App
app = FastAPI(
    title="StadiumIQ",
    description="GenAI-enabled Stadium Operations App for FIFA World Cup 2026",
    version="1.0.0"
)

# Enable CORS for hackathon demo compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Feature Routers under /api
app.include_router(navigator.router, prefix="/api", tags=["Navigator"])
app.include_router(crowd.router, prefix="/api/crowd", tags=["Crowd Intelligence"])
app.include_router(volunteer.router, prefix="/api/volunteer", tags=["Volunteer / Staff Assistant"])
app.include_router(sustainability.router, prefix="/api/sustainability", tags=["Sustainability Tracker"])

# Serve frontend/index.html at root "/"
@app.get("/", response_class=HTMLResponse)
async def get_index():
    """
    Serves the main frontend user interface.
    """
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if not frontend_path.exists():
        logger.error(f"frontend/index.html not found at: {frontend_path}")
        return HTMLResponse(
            content="<h3>Error: frontend/index.html not found!</h3>",
            status_code=404
        )
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"Error reading frontend/index.html: {e}")
        return HTMLResponse(
            content=f"<h3>Error loading index.html: {str(e)}</h3>",
            status_code=500
        )

# Optional: Mount assets directory if it exists
frontend_dir = Path(__file__).parent.parent / "frontend"
assets_dir = frontend_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
