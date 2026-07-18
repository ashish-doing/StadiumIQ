from fastapi import APIRouter, HTTPException
from backend.models import CrowdStatusResponse, CrowdAlertRequest, CrowdAlertResponse
from backend.data.crowd_simulator import get_crowd_status
from backend.gemini_client import generate_crowd_alerts

router = APIRouter()

@router.get("/status", response_model=CrowdStatusResponse)
async def get_current_crowd_status():
    """
    Returns simulated live density and trends across Zones A, B, C, and D.
    """
    try:
        status = get_crowd_status()
        return CrowdStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate crowd status: {str(e)}")

@router.post("/alert", response_model=CrowdAlertResponse)
async def analyze_crowd_alerts(req: CrowdAlertRequest):
    """
    Crowd Control Center: Analyzes live density metrics and asks Gemini to
    recommend operational alerts and flow suggestions.
    """
    if not req.zones:
        raise HTTPException(status_code=400, detail="Zones data cannot be empty.")
    
    # Format zone status as standard dictionary for prompt
    zones_list = [zone.dict() for zone in req.zones]
    
    result = generate_crowd_alerts(
        zones_data=zones_list,
        match_phase=req.match_phase or "N/A",
        simulated_time=req.simulated_time or "N/A"
    )
    
    return CrowdAlertResponse(
        alerts=result.get("alerts", []),
        flow_suggestion=result.get("flow_suggestion", "")
    )
