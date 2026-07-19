# StadiumIQ — Architecture

## Overview

StadiumIQ is a four-router FastAPI backend behind a single Gemini choke point. Every feature — Navigator, Crowd Intelligence, Volunteer Assistant, Sustainability — follows the same discipline: pull real structured data, inject it into the prompt as grounding context, and instruct Gemini not to answer beyond what's provided. A single-file vanilla JS frontend consumes all four endpoints and adds a live Leaflet GPS map layered on top of the real host-venue coordinates.

---

## System Diagram

```mermaid
flowchart TD
    subgraph CLIENT["🖥️ CLIENT LAYER"]
        UI["frontend/index.html\n━━━━━━━━━━━━━━━\nSingle-file vanilla JS\n4 tabs, no build step"]
        MAP["Leaflet GPS Map\n━━━━━━━━━━━━━━━\nReal MetLife Stadium coords\nnavigator.geolocation.watchPosition\nhaversine distance to nearest gate"]
        UI --> MAP
    end

    subgraph API["⚙️ FASTAPI LAYER"]
        MAIN["backend/main.py\n━━━━━━━━━━━━━━━\nCORS · router mounting\nStatic file serving"]
        NAV["navigator.py\nPOST /api/navigate"]
        CROWD["crowd.py\nGET /api/crowd/status\nPOST /api/crowd/alert"]
        VOL["volunteer.py\nPOST /api/volunteer/query"]
        SUS["sustainability.py\nPOST /api/sustainability/estimate"]
        MAIN --> NAV
        MAIN --> CROWD
        MAIN --> VOL
        MAIN --> SUS
    end

    subgraph GROUND["📊 GROUNDING DATA"]
        SMAP["stadium_map.json\n━━━━━━━━━━━━━━━\nGates, zones, restrooms,\nfirst aid stations"]
        KB["volunteer_kb.json\n━━━━━━━━━━━━━━━\n8 protocol entries\nkeyword-matched"]
        SIM["crowd_simulator.py\n━━━━━━━━━━━━━━━\nSeeded, time-based\nzone density generator"]
        ADJ["ZONE_GATE_ADJACENCY\n━━━━━━━━━━━━━━━\nHardcoded in gemini_client.py\nPrevents ungrounded redirects"]
    end

    subgraph AI["🤖 AI LAYER"]
        GC["gemini_client.py\n━━━━━━━━━━━━━━━\nSingle choke point\nAll 4 generate_* functions\nModel: gemini-3.1-flash-lite"]
        GEMINI["Gemini API"]
        GC --> GEMINI
    end

    NAV -->|map_data| SMAP
    NAV --> GC
    CROWD -->|density| SIM
    CROWD -->|adjacency| ADJ
    CROWD --> GC
    VOL -->|matched entries| KB
    VOL --> GC
    SUS -->|computed locally| SUS
    SUS --> GC

    UI -->|fetch| NAV
    UI -->|fetch| CROWD
    UI -->|fetch| VOL
    UI -->|fetch| SUS
```

---

## Request Flow — Fan Navigator

```mermaid
sequenceDiagram
    participant User
    participant UI as frontend/index.html
    participant NAV as navigator.py
    participant GC as gemini_client.py
    participant Gemini

    User->>UI: "How do I get to my seat from the metro in Hindi"
    UI->>UI: highlightGate() clears previous pin
    UI->>NAV: POST /api/navigate {query, language}
    NAV->>NAV: Load stadium_map.json
    NAV->>GC: generate_navigation_response(query, lang, map_data)
    GC->>Gemini: prompt with map_data as grounding context
    Note over GC,Gemini: "Do not invent gates, zones,\nseating blocks not in the data"
    Gemini-->>GC: {answer, detected_language}
    GC-->>NAV: parsed JSON
    NAV-->>UI: {answer, detected_language}
    UI->>UI: highlightGate(answer) — pulses matching gate pin
    UI-->>User: Response rendered + map highlight
```

---

## Request Flow — Crowd Intelligence (Adjacency-Grounded)

```mermaid
sequenceDiagram
    participant Poll as 5s poll loop
    participant UI as frontend/index.html
    participant CROWD as crowd.py
    participant SIM as crowd_simulator.py
    participant GC as gemini_client.py
    participant Gemini

    Poll->>UI: every 5 seconds
    UI->>CROWD: GET /api/crowd/status
    CROWD->>SIM: get current zone densities
    SIM-->>CROWD: [{zone_name, capacity_pct, trend}, ...]
    CROWD-->>UI: zone data
    UI->>UI: render zone cards, color by capacity

    alt zone crosses 80% OR match_phase changed
        UI->>CROWD: POST /api/crowd/alert {zones, match_phase}
        CROWD->>GC: generate_crowd_alerts(zones, phase, time)
        GC->>Gemini: prompt with zones + ZONE_GATE_ADJACENCY
        Note over GC,Gemini: "You MUST use the adjacency map\n— never recommend a gate not listed"
        Gemini-->>GC: {alerts, flow_suggestion}
        GC-->>CROWD: parsed JSON
        CROWD-->>UI: alerts + flow_suggestion
        UI-->>Poll: render alert cards
    end
```

This is the flow the grounding fix targets directly: before the adjacency map was added to the prompt, Gemini could recommend redirecting Zone B traffic to Gate D — a real gate, but not actually adjacent to Zone B. `ZONE_GATE_ADJACENCY` closes that gap by making the correct mapping part of the prompt context, not something the model has to infer.

---

## Request Flow — Volunteer Assistant

```mermaid
sequenceDiagram
    participant User
    participant UI as frontend/index.html
    participant VOL as volunteer.py
    participant KB as volunteer_kb.json
    participant GC as gemini_client.py
    participant Gemini

    User->>UI: "What's the protocol for a medical emergency in Section 114?"
    UI->>VOL: POST /api/volunteer/query {query}
    VOL->>KB: keyword-match query against 8 entries
    alt match found
        KB-->>VOL: matched entry/entries
        VOL->>GC: generate_volunteer_response(query, matched_entries)
        GC->>Gemini: prompt restricted to matched entries only
        Gemini-->>GC: {answer}
        GC-->>VOL: answer
        VOL-->>UI: {answer, grounded_on: ["Medical Emergency Protocol"]}
    else no match
        KB-->>VOL: empty list
        VOL->>GC: generate_volunteer_response(query, [])
        GC->>Gemini: prompt with empty context
        Note over GC,Gemini: Instructed to say "not in Knowledge Base"\nrather than invent an answer
        Gemini-->>GC: honest non-match response
        GC-->>VOL: answer
        VOL-->>UI: {answer, grounded_on: []}
    end
    UI-->>User: Answer + source badges (if any)
```

---

## Request Flow — Sustainability Tracker

```mermaid
sequenceDiagram
    participant User
    participant UI as frontend/index.html
    participant SUS as sustainability.py
    participant GC as gemini_client.py
    participant Gemini

    User->>UI: Adjusts sliders (auto-balance to 100%), clicks Calculate
    UI->>SUS: POST /api/sustainability/estimate {fan_count, transport_split, avg_distance_km}
    SUS->>SUS: Compute CO2 locally via EMISSION_FACTORS\n(car 0.171, bus 0.054, metro 0.028 kg/km)
    Note over SUS: Math is deterministic Python —\nGemini is not used for the numbers
    SUS->>GC: generate_sustainability_suggestions(fan_count, split, distance, total_co2)
    GC->>Gemini: prompt with the real computed numbers
    Note over GC,Gemini: "Tailor suggestions to the actual split —\nif car % is high, recommend carpool incentives"
    Gemini-->>GC: {suggestions: [...]}
    GC-->>SUS: list of suggestion strings
    SUS-->>UI: {total_kg_co2, per_fan_kg_co2, suggestions}
    UI-->>User: Stat cards + tailored suggestions
```

Note the split of responsibility: the carbon math is deterministic Python, never delegated to Gemini. Gemini's job is strictly the qualitative recommendations layered on top of real numbers — a smaller, more auditable surface for the model to get wrong.

---

## Component Reference

| Component | File | Responsibility |
|---|---|---|
| **Entrypoint** | `backend/main.py` | FastAPI app, CORS, router mounting, serves `frontend/index.html` |
| **Gemini Client** | `backend/gemini_client.py` | Single choke point — all 4 `generate_*` functions, model config, `ZONE_GATE_ADJACENCY` |
| **Schemas** | `backend/models.py` | Pydantic request/response models for all 4 endpoints |
| **Navigator Router** | `backend/routers/navigator.py` | Loads `stadium_map.json`, calls `generate_navigation_response` |
| **Crowd Router** | `backend/routers/crowd.py` | Reads `crowd_simulator.py`, calls `generate_crowd_alerts` |
| **Volunteer Router** | `backend/routers/volunteer.py` | Keyword-matches `volunteer_kb.json`, calls `generate_volunteer_response` |
| **Sustainability Router** | `backend/routers/sustainability.py` | Computes CO₂ locally, calls `generate_sustainability_suggestions` |
| **Stadium Map** | `backend/data/stadium_map.json` | Gates, zones, restrooms, first-aid stations — Navigator grounding source |
| **Volunteer KB** | `backend/data/volunteer_kb.json` | 8 protocol entries — Volunteer grounding source |
| **Crowd Simulator** | `backend/data/crowd_simulator.py` | Seeded, time-based density generator — not live sensor data |
| **Frontend** | `frontend/index.html` | Single-file dashboard, 4 tabs, Leaflet GPS map, auto-balancing sliders |
| **Tests** | `tests/test_stadiumiq.py` | 17 unit tests — requires a `GEMINI_API_KEY` env var (dummy value works) |
| **Model Checker** | `scripts/check_model.py` | Dev utility — tests live model availability against your API key |
| **Landing Page** | `docs/index.html` | GitHub Pages marketing site |

---

## Grounding Discipline

Every one of the four `generate_*` functions in `gemini_client.py` follows the same pattern:

1. Real structured data (map, KB, density, adjacency, or computed numbers) is serialized and injected directly into the prompt
2. The prompt explicitly instructs Gemini not to invent anything outside that context
3. On any error (API failure, malformed JSON), the function fails to a static, honest fallback string rather than a silent guess

This is the difference between "grounded" as a marketing word and grounded as an enforced code pattern — the constraint lives in the prompt template every single call goes through, not in a policy nobody checks.

---

## Key Version Constraints

| Package | Version | Reason |
|---|---|---|
| `google-generativeai` | pinned | Legacy SDK — Google's support has ended in favor of `google-genai`; migration tracked as a non-blocking follow-up (see `CONTEXT.md`) |
| `gemini-3.1-flash-lite` | — | Chosen after `gemini-2.5-flash-lite` began returning premature 404s for new API keys mid-build; confirmed via `scripts/check_model.py` |
| `fastapi` | `0.115.x` | Stable, async, auto-generated `/docs` |
| `python` | `3.11` | Docker base image target |
| Leaflet | `1.9.4` (CDN) | No API key required, unlike Google Maps JS |

---

## Deployment Architecture

```mermaid
flowchart TD
    subgraph LOCAL["Local Development"]
        L1["python -m venv venv"]
        L2["pip install -r requirements.txt"]
        L3["uvicorn backend.main:app --reload"]
        L1 --> L2 --> L3
    end

    subgraph GIT["Git"]
        G1["git push origin main"]
        G2["GitHub repo\nashish-doing/StadiumIQ"]
        G1 --> G2
    end

    subgraph RENDER["Render (Docker Web Service)"]
        R1["Dockerfile\nPython 3.11-slim base"]
        R2["requirements.txt"]
        R3["GEMINI_API_KEY\nenvironment secret"]
        R4["uvicorn on $PORT\n(Render-assigned, not hardcoded)"]
        R1 --> R2 --> R3 --> R4
    end

    subgraph PAGES["GitHub Pages"]
        P1["docs/index.html\nLanding page"]
    end

    G2 -->|auto-deploy on commit| RENDER
    G2 --> PAGES
```

---

*Built for PromptWars Virtual — Challenge 4: Smart Stadiums & Tournament Operations*