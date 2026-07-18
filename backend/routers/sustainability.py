from fastapi import APIRouter, HTTPException
from backend.models import SustainabilityRequest, SustainabilityResponse
from backend.gemini_client import generate_sustainability_suggestions

router = APIRouter()

# Emission factors (kg CO2 per passenger-kilometer)
# Sources: 
# - Car: 0.171 kg CO2/passenger-km (Assuming average petrol car, UK DEFRA 2023 / US EPA equivalent)
# - Bus: 0.054 kg CO2/passenger-km (Average transit bus, UK DEFRA 2023)
# - Metro: 0.028 kg CO2/passenger-km (Transit rail / Metro, UK DEFRA 2023)
# - Walk: 0.000 kg CO2/passenger-km (Zero tailpipe emissions)
EMISSION_FACTORS = {
    "car": 0.171,
    "bus": 0.054,
    "metro": 0.028,
    "walk": 0.000
}

@router.post("/estimate", response_model=SustainabilityResponse)
async def estimate_sustainability(req: SustainabilityRequest):
    """
    Sustainability Tracker: Estimate carbon footprint based on fan travel modes and distance,
    and generate custom AI recommendations to reduce the carbon impact.
    """
    if req.fan_count <= 0:
        raise HTTPException(status_code=400, detail="Fan count must be positive.")
    if req.avg_distance_km <= 0:
        raise HTTPException(status_code=400, detail="Average distance must be positive.")
    
    # Check that transport split percentages sum close to 100%
    total_split = req.transport_split.car + req.transport_split.bus + req.transport_split.metro + req.transport_split.walk
    if not (95.0 <= total_split <= 105.0):
        # Allow small deviation but reject wild numbers
        raise HTTPException(status_code=400, detail=f"Transport split percentages must sum to ~100% (got {total_split}%).")
        
    # Calculate CO2 emissions
    # Mode share in decimals
    car_share = req.transport_split.car / 100.0
    bus_share = req.transport_split.bus / 100.0
    metro_share = req.transport_split.metro / 100.0
    walk_share = req.transport_split.walk / 100.0
    
    # Total passenger-kilometers per mode
    car_km = req.fan_count * car_share * req.avg_distance_km
    bus_km = req.fan_count * bus_share * req.avg_distance_km
    metro_km = req.fan_count * metro_share * req.avg_distance_km
    
    # Carbon emissions per mode in kg CO2
    car_co2 = car_km * EMISSION_FACTORS["car"]
    bus_co2 = bus_km * EMISSION_FACTORS["bus"]
    metro_co2 = metro_km * EMISSION_FACTORS["metro"]
    
    total_co2 = car_co2 + bus_co2 + metro_co2
    per_fan_co2 = total_co2 / req.fan_count
    
    # Convert transport split object to dict for Gemini client
    split_dict = {
        "car": req.transport_split.car,
        "bus": req.transport_split.bus,
        "metro": req.transport_split.metro,
        "walk": req.transport_split.walk
    }
    
    # Call Gemini to get recommendations
    suggestions = generate_sustainability_suggestions(
        fan_count=req.fan_count,
        transport_split=split_dict,
        avg_distance_km=req.avg_distance_km,
        total_kg_co2=total_co2
    )
    
    return SustainabilityResponse(
        total_kg_co2=round(total_co2, 2),
        per_fan_kg_co2=round(per_fan_co2, 4),
        suggestions=suggestions
    )
