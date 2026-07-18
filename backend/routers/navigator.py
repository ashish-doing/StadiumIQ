import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.models import NavigatorRequest, NavigatorResponse
from backend.gemini_client import generate_navigation_response

router = APIRouter()

# Load stadium map database
MAP_PATH = Path(__file__).parent.parent / "data" / "stadium_map.json"
if not MAP_PATH.exists():
    raise FileNotFoundError(f"Stadium map database not found at {MAP_PATH}")

with open(MAP_PATH, "r", encoding="utf-8") as f:
    stadium_map_data = json.load(f)

@router.post("/navigate", response_model=NavigatorResponse)
async def navigate_stadium(req: NavigatorRequest):
    """
    Fan Navigator: Accept fan's navigation query, ground it in stadium_map.json,
    and return Gemini's guidance in the same language.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Generate the navigation guidance using Gemini client
    result = generate_navigation_response(
        query=req.query,
        requested_language=req.language,
        map_data=stadium_map_data
    )
    
    return NavigatorResponse(
        answer=result.get("answer", ""),
        detected_language=result.get("detected_language", "English")
    )
