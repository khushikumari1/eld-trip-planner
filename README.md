# ELD Trip Planner

A full-stack application that plans truck driver trips with **FMCSA Hours of Service (HOS) compliance**. Takes trip inputs, calculates routes, simulates HOS rules step-by-step, and generates compliant Driver Daily Logs (ELD logs).

## Features

- **Route Planning**: Calculates optimal driving route with distance and duration
- **HOS Simulation Engine**: Time-based simulation (not simple division) that tracks all compliance limits
- **ELD Log Generation**: FMCSA-format 24-hour grid logs with 4 duty statuses
- **Interactive Map**: Route polyline with color-coded stop markers
- **Multi-day Support**: Handles trips requiring multiple days with proper resets

## FMCSA Rules Implemented

| Rule | Description |
|------|-------------|
| 11-Hour Driving | Max 11 hours driving after 10 consecutive hours off |
| 14-Hour Window | Cannot drive past 14th hour after coming on duty |
| 30-Minute Break | Required after 8 cumulative hours of driving |
| 10-Hour Reset | 10 consecutive hours off resets daily limits |
| 70-Hour/8-Day | Cannot drive after 70 hours on-duty in 8 days |
| 34-Hour Restart | Optional full cycle reset |

## Tech Stack

- **Backend**: Django 5 + Django REST Framework
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Maps**: Leaflet.js + OpenStreetMap tiles
- **Routing**: OpenRouteService API (free tier)
- **ELD Grid**: HTML5 Canvas rendering

## Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your ORS API key
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Project Structure
```
├── backend/
│   ├── config/          # Django settings, URLs, WSGI
│   ├── trips/
│   │   ├── services/
│   │   │   ├── routing.py       # ORS geocoding + directions
│   │   │   ├── hos_engine.py    # HOS simulation engine (core)
│   │   │   └── log_generator.py # Timeline → ELD logs
│   │   ├── views.py             # API endpoints
│   │   ├── serializers.py       # Request/response validation
│   │   └── models.py            # Data models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm.jsx     # Input form
│   │   │   ├── MapView.jsx      # Route map with stops
│   │   │   └── ELDLogSheet.jsx  # Canvas ELD grid renderer
│   │   ├── services/api.js      # API client
│   │   └── App.jsx              # Main app layout
│   └── package.json
└── docs/
    ├── CONTINUATION_GUIDE.md    # For AI to continue/deploy
    ├── SYSTEM_DESIGN.md         # Architecture + API design
    ├── DEPLOYMENT.md            # Deploy to Render + Vercel
    └── LOOM_VIDEO_SCRIPT.md     # 3-5 min video script
```

## Assumptions

- Property-carrying driver, 70hrs/8days
- No adverse driving conditions
- Fueling at least once every 1,000 miles
- 1 hour for pickup and drop-off operations
- Average speed derived from route calculation
