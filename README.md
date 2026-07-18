# StadiumIQ — GenAI Stadium Operations for FIFA World Cup 2026

StadiumIQ is a GenAI-enabled stadium operations and fan experience platform designed for the FIFA World Cup 2026. It leverages Google Gemini 2.5 Flash to orchestrate fan navigation, real-time crowd intelligence, volunteer/staff protocols, and match-day sustainability planning.

This project was built from scratch using **Google Antigravity**, a state-of-the-art agentic AI coding companion.

---

## Technical Stack
- **Backend:** FastAPI, Python 3.11, Uvicorn
- **GenAI Client:** `google-generativeai` Python SDK (model: `gemini-2.5-flash`)

- **Frontend:** Vanilla HTML5, CSS3 Grid/Variables/Animations, and Vanilla JavaScript (SPA, no framework, no build steps)
- **Deployment:** Docker (optimized for Hugging Face Spaces)

---

## Project Structure
```
stadiumiq/
├── backend/
│   ├── data/
│   │   ├── crowd_simulator.py      # Seeded, time-based live crowd density simulator
│   │   ├── stadium_map.json        # Grounding map database
│   │   └── volunteer_kb.json       # Operational protocols knowledge base
│   ├── routers/
│   │   ├── crowd.py                # Heatmap & crowd alerts API
│   │   ├── navigator.py            # Multilingual fan assistant API
│   │   ├── sustainability.py       # Transit footprint estimator API
│   │   └── volunteer.py            # Staff guideline RAG API
│   ├── gemini_client.py            # Single point of entry for Gemini SDK configuration & calls
│   ├── main.py                     # FastAPI entrypoint, CORS setup, and SPA routing
│   └── models.py                   # Pydantic schemas for requests and responses
├── frontend/
│   └── index.html                  # Responsive dashboard UI (embedded CSS + JS)
├── .env.example                    # Template environment variables
├── Dockerfile                      # Container setup for Hugging Face Spaces (Port 7860)
├── requirements.txt                # Pinned dependencies
└── README.md                       # This documentation
```

---

## Local Setup & Installation

### 1. Clone & Navigate to Project
```bash
cd stadiumiq
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your Gemini API key:
```env
GEMINI_API_KEY=AIzaSyYourActualKeyHere...
```
*Note: The app will fail to start and throw a critical validation error if `GEMINI_API_KEY` is not present.*

### 5. Run the Application
Start the FastAPI server locally in reload mode:
```bash
uvicorn backend.main:app --reload
```
Once running, open your browser and navigate to:
**`http://127.0.0.1:8000`**

---

## Deploying to Hugging Face Spaces

StadiumIQ is ready to deploy directly as a **Docker SDK Space** on Hugging Face:
1. Create a new Space on Hugging Face.
2. Select **Docker** as the SDK.
3. Choose the **Blank** template or upload the files directly.
4. Go to **Settings** in your Space, scroll to **Repository Secrets**, and add:
   - Name: `GEMINI_API_KEY`
   - Value: `AIzaSy...` (your Gemini API key)
5. Push the code repository. Hugging Face will automatically build the image using the `Dockerfile` and run the app on port `7860`.

---

## Live Demo Queries to Validate

You can use the following queries to test the live capabilities of the app:

### 1. Fan Navigator Query
- **Query:** `"How do I get to my seat from the metro station in Hindi"`
- **Expected Outcome:** Gemini detects the language is Hindi and responds in Hindi with instructions grounded in `stadium_map.json` (e.g. using Gate A and walking along the North Pedestrian Walkway from Arena Central Metro Station).

### 2. Volunteer Assistant Query
- **Query:** `"What's the protocol for a medical emergency in Section 114?"`
- **Expected Outcome:** The backend performs a string-matching search, retrieves the "Medical Emergency Protocol" from `volunteer_kb.json`, and feeds it to Gemini. Gemini answers with the specific radio channel and steps, returning `grounded_on: ["Medical Emergency Protocol"]`.

### 3. Sustainability Calculator Query
- **Inputs:**
  - Fan Count: `40000`
  - Transport Split: `Car = 60%`, `Bus = 15%`, `Metro = 20%`, `Walk = 5%`
  - Average Distance: `12 km`
- **Expected Outcome:**
  - Total CO2 Emitted: `55,824.0 kg CO2`
  - Per Fan Emission: `1.396 kg CO2`
  - AI Recommendations: Actionable transit advice tailored to the high (60%) car usage.
