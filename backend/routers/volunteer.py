import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException
from backend.models import VolunteerQueryRequest, VolunteerQueryResponse
from backend.gemini_client import generate_volunteer_response

router = APIRouter()

# Load volunteer knowledge base
KB_PATH = Path(__file__).parent.parent / "data" / "volunteer_kb.json"
if not KB_PATH.exists():
    raise FileNotFoundError(f"Volunteer KB not found at {KB_PATH}")

with open(KB_PATH, "r", encoding="utf-8") as f:
    volunteer_kb_data = json.load(f)

def retrieve_protocols(query: str, kb: List[dict], limit: int = 2) -> List[dict]:
    """
    Performs keyword and phrase-based scoring to retrieve the top `limit` protocols.
    """
    query_lower = query.lower()
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "for", "to", "in", "on", "at", "of", "with", "what", "whats", "how", "do", "i", "we", "you", "protocol"}
    words = [w.strip("?,.!") for w in query_lower.split() if w.strip("?,.!") not in stopwords]
    
    scored = []
    for entry in kb:
        score = 0
        title_lower = entry["title"].lower()
        desc_lower = entry["description"].lower()
        proto_lower = entry["protocol"].lower()
        
        # Priority boost for matching specific protocol domains
        if ("medical" in query_lower or "injured" in query_lower or "sick" in query_lower or "first aid" in query_lower) and "medical" in title_lower:
            score += 15
        if ("lost" in query_lower or "child" in query_lower or "missing" in query_lower) and "lost" in title_lower:
            score += 15
        if ("access" in query_lower or "wheelchair" in query_lower or "mobility" in query_lower) and "accessibility" in title_lower:
            score += 15
        if ("weather" in query_lower or "lightning" in query_lower or "storm" in query_lower or "rain" in query_lower) and "weather" in title_lower:
            score += 15
        if ("security" in query_lower or "suspicious" in query_lower or "fight" in query_lower or "package" in query_lower) and "security" in title_lower:
            score += 15
        if ("media" in query_lower or "press" in query_lower or "reporter" in query_lower) and "media" in title_lower:
            score += 15
        if "lost" in query_lower and ("found" in query_lower or "belonging" in query_lower or "item" in query_lower) and "found" in title_lower:
            score += 15
        if ("ticket" in query_lower or "seat" in query_lower or "dispute" in query_lower or "double" in query_lower) and "ticket" in title_lower:
            score += 15
        if ("drunk" in query_lower or "intoxicated" in query_lower or "alcohol" in query_lower or "disruptive" in query_lower) and "intoxicated" in title_lower:
            score += 15
        if ("gate" in query_lower or "scanner" in query_lower or "delay" in query_lower or "offline" in query_lower) and "gate" in title_lower:
            score += 15
            
        # Word overlap scoring
        for word in words:
            if not word or len(word) < 2:
                continue
            if word in title_lower:
                score += 5
            if word in desc_lower:
                score += 2
            if word in proto_lower:
                score += 1
                
        if score > 0:
            scored.append((score, entry))
            
    # Sort by score descending and take top entries
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]

@router.post("/query", response_model=VolunteerQueryResponse)
async def query_volunteer_kb(req: VolunteerQueryRequest):
    """
    Staff / Volunteer Assistant: Accept query, search volunteer_kb.json,
    ground response using Gemini, and return the answer + matched protocols.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Retrieve top 2 grounding protocols
    matched_protocols = retrieve_protocols(req.query, volunteer_kb_data, limit=2)
    
    # Generate the grounded response from Gemini
    result = generate_volunteer_response(query=req.query, kb_entries=matched_protocols)
    
    # List the titles of the grounded protocols
    grounded_titles = [proto["title"] for proto in matched_protocols]
    
    # If no protocols matched at all, provide a default response indicating no grounding
    if not matched_protocols:
        answer = "I'm sorry, but that query does not seem to match any protocol in my Knowledge Base."
    else:
        answer = result.get("answer", "")
        
    return VolunteerQueryResponse(
        answer=answer,
        grounded_on=grounded_titles
    )
