# Agent Deployment Prompt

Copy and paste the following prompt to another AI agent to continue from where we left off and deploy the application.

---

## PROMPT START

You are a senior full-stack engineer. You have a COMPLETE codebase for an ELD Trip Planner application in the `eld-trip-planner/` directory. The code is written and compiles cleanly. Your job is to **finalize, test, and deploy it to production**.

### Project Context
This is a full-stack app (Django + React) that takes truck trip inputs, calculates routes via OpenRouteService, simulates FMCSA Hours of Service rules step-by-step, and generates compliant ELD (Electronic Logging Device) daily logs. The code is DONE — you need to wire it up, test it, and deploy it.

### Project Structure
```
eld-trip-planner/
├── backend/                    # Django 5 + DRF
│   ├── config/settings.py      # Django settings (uses python-dotenv)
│   ├── trips/services/
│   │   ├── routing.py          # OpenRouteService geocoding + directions
│   │   ├── hos_engine.py       # HOS simulation engine (core logic)
│   │   └── log_generator.py    # Converts timeline → ELD daily logs
│   ├── trips/views.py          # POST /api/trip-plan/ endpoint
│   ├── trips/serializers.py    # DRF serializers
│   ├── requirements.txt        # Python dependencies (pinned versions)
│   ├── Procfile                # For Render/Railway
│   └── .env.example            # Template for environment variables
├── frontend/                   # React 18 + Vite + Tailwind
│   ├── src/components/
│   │   ├── TripForm.jsx        # Input form
│   │   ├── MapView.jsx         # Leaflet map with route + stops
│   │   └── ELDLogSheet.jsx     # Canvas-rendered ELD log grid
│   ├── src/services/api.js     # Axios API client
│   ├── package.json            # Node dependencies (pinned versions)
│   ├── vercel.json             # Vercel deployment config
│   └── .env.example            # Template for env vars
└── docs/
    ├── SYSTEM_DESIGN.md        # Architecture, API spec, edge cases
    ├── DEPLOYMENT.md           # Step-by-step deploy instructions
    └── CONTINUATION_GUIDE.md   # Full context for continuing work
```

### YOUR TASKS (in order)

#### 1. Get an OpenRouteService API Key
- Sign up at https://openrouteservice.org/dev/#/signup (free, 2000 req/day)
- Create a file `backend/.env` with: `ORS_API_KEY=your_actual_key`

#### 2. Set Up and Test Backend Locally
```bash
cd eld-trip-planner/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env → add your ORS_API_KEY
python manage.py migrate
python manage.py runserver
```
Test with:
```bash
curl -X POST http://localhost:8000/api/trip-plan/ \
  -H "Content-Type: application/json" \
  -d '{"current_location":"Dallas, TX","pickup_location":"Houston, TX","dropoff_location":"Los Angeles, CA","current_cycle_used":20}'
```
Verify the response contains: route_coordinates, stops, daily_logs, summary.

#### 3. Set Up and Test Frontend Locally
```bash
cd eld-trip-planner/frontend
npm install
npm run dev
```
Open http://localhost:5173, enter trip details, verify:
- Map shows route polyline with colored stop markers
- ELD Logs tab shows daily log grids with correct duty status lines
- Totals per day sum to 24 hours

#### 4. Fix Any Issues
- If ORS API returns errors, check the API key and rate limits
- If CORS errors occur, verify `CORS_ALLOW_ALL_ORIGINS = True` in DEBUG mode
- If canvas doesn't render, check browser console for JS errors

#### 5. Deploy Backend to Render.com
1. Push code to GitHub
2. Create new Web Service on Render.com
3. Settings:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Add environment variables:
   - `DJANGO_SECRET_KEY` → generate a random one
   - `DJANGO_DEBUG` → `False`
   - `ALLOWED_HOSTS` → `your-app-name.onrender.com`
   - `ORS_API_KEY` → your key
   - `CORS_ALLOWED_ORIGINS` → `https://your-frontend.vercel.app`
5. Deploy and note the URL (e.g., `https://eld-trip-planner-api.onrender.com`)

#### 6. Deploy Frontend to Vercel
1. Import the repo on Vercel
2. Settings:
   - Root Directory: `frontend`
   - Framework: Vite
3. Add environment variable:
   - `VITE_API_BASE_URL` → `https://your-backend.onrender.com/api`
4. Deploy

#### 7. Verify Production
- Open the Vercel URL
- Submit a test trip
- Confirm map and ELD logs render correctly
- Test edge cases: short trip (50 miles), long trip (2500 miles), high cycle usage (65 hours)

### KEY TECHNICAL DETAILS

**API Endpoint**: `POST /api/trip-plan/`
- Input: `{current_location, pickup_location, dropoff_location, current_cycle_used}`
- Output: `{total_distance_miles, total_duration_hours, route_coordinates, stops, daily_logs, summary}`

**HOS Rules (already implemented in hos_engine.py)**:
- 11-hour driving limit (resets after 10hr off)
- 14-hour window (off-duty does NOT pause it, resets after 10hr off)
- 30-min break after 8 cumulative driving hours (resets break clock)
- 10-hour off-duty reset (resets 11hr + 14hr clocks)
- 70-hour/8-day cycle (resets after 34hr restart)
- Fuel stops every 1000 miles (30 min, counts as on-duty)
- Pickup/dropoff: 1 hour each (on-duty not driving)

**ELD Log Format**:
- Each log = one calendar day (midnight to midnight)
- 4 status rows: OFF, SB (Sleeper Berth), D (Driving), ON (On Duty Not Driving)
- Segments have start_hour (0-24) and end_hour (0-24)
- Total hours per day MUST equal 24
- Remarks list location at each duty status change

**Frontend ELD Rendering**:
- Uses HTML5 Canvas (2x scale for retina)
- Draws grid lines, hour labels, status labels
- Draws colored horizontal lines for each segment
- Draws vertical lines for transitions between statuses

### IMPORTANT NOTES
- Do NOT modify the HOS engine logic — it correctly implements FMCSA rules from the official 2022 guide
- The routing service uses ORS heavy goods vehicle (HGV) profile for truck-appropriate routes
- If Render free tier is slow on first request (cold start), that's expected — mention it in the Loom video
- The frontend Vite proxy (`/api` → `localhost:8000`) only works in dev; production uses VITE_API_BASE_URL

### DELIVERABLES
1. ✅ Live hosted version (Vercel frontend + Render backend)
2. ✅ GitHub repo with clean code
3. Record a 3-5 minute Loom video (script in `docs/LOOM_VIDEO_SCRIPT.md`)

## PROMPT END
