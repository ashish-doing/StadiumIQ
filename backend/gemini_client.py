import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Retrieve API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.critical("GEMINI_API_KEY environment variable is missing!")
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please provide a valid API key in your environment or .env file."
    )

# NOTE: using google-generativeai (legacy SDK). Google's recommended
# replacement is google-genai. Pinned here for stability during the
# hackathon build; migration tracked as a follow-up, not blocking —
# the legacy SDK is still functional and supported as of this build.

# Configure the generative AI client
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.1-flash-lite")

# Zone-to-gate adjacency, used to ground crowd redirect suggestions so
# Gemini can't recommend a gate that isn't actually near the congested zone.
ZONE_GATE_ADJACENCY = {
    "Zone A": "Gate A (North / Metro)",
    "Zone B": "Gate B (South / Parking)",
    "Zone C": "Gate C (East / Bus)",
    "Zone D": "Gate D (West / VIP & Access)"
}


def generate_navigation_response(query: str, requested_language: Optional[str], map_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls Gemini to generate navigation instructions grounded strictly in the stadium map data.
    Auto-detects language if requested_language is not provided and responds in the detected language.
    """
    prompt = f"""
You are StadiumIQ, the GenAI-enabled navigation assistant for the FIFA World Cup 2026.
Your task is to answer a fan's navigation query based STRICTLY on the official stadium map data provided below.
Do not invent gates, zones, seating blocks, concession stands, parking lots, restrooms, or transportation options.
If the map data does not contain the answer, politely tell the fan that the information is not in the official stadium map database.

Grounding Context (Stadium Map JSON):
{json.dumps(map_data, indent=2)}

User's Query:
"{query}"

Requested Language: {requested_language if requested_language else "Auto-detect (respond in the language of the query: English, Hindi, Spanish, or Arabic)"}

You must return a JSON object with the following fields:
- "answer": (string) Your complete, friendly, and helpful navigation instructions in the target language.
- "detected_language": (string) The language you detected and wrote the answer in (e.g., "English", "Hindi", "Spanish", "Arabic").
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        if "answer" not in result:
            result["answer"] = response.text
        if "detected_language" not in result:
            result["detected_language"] = requested_language or "English"
        return result
    except Exception as e:
        logger.error(f"Error in generate_navigation_response: {e}")
        return {
            "answer": f"Error communicating with Gemini: {str(e)}",
            "detected_language": requested_language or "English"
        }


def generate_crowd_alerts(zones_data: List[Dict[str, Any]], match_phase: str, simulated_time: str) -> Dict[str, Any]:
    """
    Calls Gemini to analyze density data and output 1-3 short operational alerts
    along with a one-line entry/exit flow suggestion. Redirect suggestions are
    grounded in ZONE_GATE_ADJACENCY so Gemini can't invent a nearby gate.
    """
    prompt = f"""
You are the StadiumIQ Crowd Intelligence AI. You monitor live crowd density across different stadium zones.
Analyze the current live status and generate operational directives for stadium operations staff.

Match Phase: {match_phase} ({simulated_time})
Live Zone Densities:
{json.dumps(zones_data, indent=2)}

Zone-to-Gate Adjacency (use this to pick which gate to redirect fans toward — never recommend a gate not listed here for that zone):
{json.dumps(ZONE_GATE_ADJACENCY, indent=2)}

Tasks:
1. Generate 1 to 3 short operational alerts (each max 20 words) addressing any zones with high capacity (especially above 80%) or rising trends, suggesting staff action (e.g. redirecting fans, opening specific gates, mobilizing volunteers, advising concession staff). When recommending a gate redirect, you MUST use the adjacency map above.
2. Generate a single, concise entry/exit flow suggestion (max 25 words) suited to the match phase.

You must return a JSON object with the following fields:
- "alerts": (array of strings) The 1-3 operational alerts.
- "flow_suggestion": (string) The one-line flow suggestion.
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        if "alerts" not in result or not isinstance(result["alerts"], list):
            result["alerts"] = ["Monitor high density zones for traffic build-up."]
        if "flow_suggestion" not in result:
            result["flow_suggestion"] = "Maintain standard entry/exit pathways."
        return result
    except Exception as e:
        logger.error(f"Error in generate_crowd_alerts: {e}")
        return {
            "alerts": ["Error generating crowd intelligence alerts."],
            "flow_suggestion": "Refer to standard gate operational manuals."
        }


def generate_volunteer_response(query: str, kb_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calls Gemini to answer volunteer queries strictly grounded in the matched KB entries.
    If no relevant entries, Gemini must output a message stating no match.
    """
    prompt = f"""
You are the StadiumIQ Staff and Volunteer Assistant.
Your job is to assist stadium staff with operational protocols based ONLY on the provided Knowledge Base (KB) articles.
Do NOT invent procedures, phone numbers, radio channels, or locations not present in the KB entries.
If the provided context is empty or doesn't address the query, answer exactly: "I'm sorry, but that query does not seem to match any protocol in my Knowledge Base."

Grounding Context (Matched KB Entries):
{json.dumps(kb_entries, indent=2)}

Staff Query:
"{query}"

You must return a JSON object with the following field:
- "answer": (string) The detailed answer grounded strictly in the provided protocols.
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        if "answer" not in result:
            result["answer"] = response.text
        return result
    except Exception as e:
        logger.error(f"Error in generate_volunteer_response: {e}")
        return {
            "answer": "Error generating response from Knowledge Base."
        }


def generate_sustainability_suggestions(
    fan_count: int,
    transport_split: Dict[str, float],
    avg_distance_km: float,
    total_kg_co2: float
) -> List[str]:
    """
    Calls Gemini to generate 2-3 specific, actionable sustainability suggestions
    tailored to the transport split, distance, and emissions.
    """
    prompt = f"""
You are the StadiumIQ Sustainability AI.
Analyze the transport emissions of fans for the current match and provide actionable transit/eco-friendly recommendations.

Inputs:
- Total Fan Attendance: {fan_count}
- Average Distance Travelled: {avg_distance_km} km
- Total CO2 Emitted: {total_kg_co2:.1f} kg
- Transport Share:
  - Private Car: {transport_split.get('car', 0.0)}%
  - Bus Transit: {transport_split.get('bus', 0.0)}%
  - Metro Transit: {transport_split.get('metro', 0.0)}%
  - Walk/Bike: {transport_split.get('walk', 0.0)}%

Generate 2 to 3 specific, actionable, and impact-focused sustainability suggestions (each max 25 words).
Tailor the suggestions to the data:
- If private car percentage is high, recommend carpool rewards, EV priority parking, or rideshare-pooling incentives.
- If metro/bus share is low, suggest late-night service extensions, transit-inclusive ticketing, or park-and-ride options.
- If walking/biking is low, suggest active travel maps, bicycle valets, or pedestrian-friendly green walkways.

You must return a JSON object with the following field:
- "suggestions": (array of strings) The 2-3 sustainability recommendations.
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        if "suggestions" not in result or not isinstance(result["suggestions"], list):
            result["suggestions"] = ["Encourage fans to use public transport.", "Implement carpooling incentives."]
        return result
    except Exception as e:
        logger.error(f"Error in generate_sustainability_suggestions: {e}")
        return ["Error generating sustainability recommendations."]