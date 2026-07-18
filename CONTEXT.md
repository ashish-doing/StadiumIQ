# Built with Google Antigravity — Build Log

This file documents how StadiumIQ was actually built inside Google Antigravity, as required for PromptWars Virtual submissions. Everything below reflects real debugging steps from the build session, not a cleaned-up retelling.

## The mission brief

The full backend, frontend, and Docker scaffold were generated from a single detailed mission prompt given to Antigravity's Agent Manager, specifying:
- Exact project structure (`backend/routers/`, `backend/data/`, `frontend/index.html`, etc.)
- Per-feature behavior for all 4 tools (Navigator, Crowd Intelligence, Volunteer Assistant, Sustainability)
- The grounding requirement: every AI response restricted to provided context, no invented gates/protocols/numbers
- Required deliverables: `requirements.txt`, `Dockerfile`, `README.md`, `.env.example`

## What Antigravity actually built, in one pass

- `backend/main.py` — FastAPI entrypoint, CORS, router mounting
- `backend/gemini_client.py` — single choke point for every Gemini call
- `backend/routers/{navigator,crowd,volunteer,sustainability}.py`
- `backend/data/{stadium_map.json, volunteer_kb.json, crowd_simulator.py}`
- `frontend/index.html`
- `requirements.txt`, `Dockerfile`, `README.md`

## Real problems hit during the build, and how they were resolved through Antigravity

**1. Dead model reference.** The original spec called for `gemini-1.5-flash`. Live testing returned 404s — the model was fully deprecated by mid-2026. Told the agent directly: *"Stop scanning for models — replace every gemini-1.5-flash reference with gemini-2.5-flash, delete find_model.py, retest."* Fixed in one pass once redirected.

**2. API project access (403/429).** The Gemini API key's backing project returned `403 Your project has been denied access` and `429 quota exceeded, limit: 0` — a Google Cloud project misconfiguration, not a code bug. Resolved outside Antigravity by generating a fresh API key from a new AI Studio project, then confirming the fix by retesting the same endpoint directly.

**3. Deployment platform pivot.** Originally targeted Hugging Face Spaces; Hugging Face's current free tier no longer permits CPU Basic on new Docker Spaces (ZeroGPU doesn't support the Docker SDK). Pivoted to Render instead, reusing a Docker deployment pattern proven on two earlier projects (RepoTerrain, ExpenseIQ).

**4. Port binding.** Docker was hardcoded to port `7860` (Hugging Face's convention). Render injects its own `$PORT`. One-line fix: `CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}`.

**5. Rate limits under test load.** Repeated manual testing plus the earlier model-scanning attempt burned through the free-tier daily quota on `gemini-2.5-flash`. Switched to `gemini-2.5-flash-lite` for a materially higher free-tier ceiling with no behavior change.

## Example prompts used inside Antigravity

```
Stop the model-scanning approach — that's the wrong fix. The actual problem is that
gemini-1.5-flash is deprecated and shut down (returns 404). Replace every reference to
"gemini-1.5-flash" across the codebase with "gemini-2.5-flash". Delete find_model.py —
it's not needed. Then restart the server and re-test the /api/navigate endpoint directly
to confirm you get a real response, not an error.
```

```
Check gemini_client.py and volunteer.py / navigator.py — the system instruction or prompt
template being sent to Gemini needs to explicitly state "only use the provided context
below, do not invent locations or protocols not present in it." Show me the current
prompt template before changing it, then fix it.
```

## Honest note on the crowd simulator

`crowd_simulator.py` generates realistic-looking zone density using seeded randomization, not live sensor or turnstile data — this is a deliberate simulation for the demo, not a live feed. In a production deployment, this same interface would be backed by real gate-scan telemetry; the simulator exists specifically so the Crowd Intelligence and alerting logic can be demoed without physical hardware.