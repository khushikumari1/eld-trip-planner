# ELD Trip Planner - Continuation Guide for AI Deployment

## Project Overview

This is a full-stack ELD (Electronic Logging Device) / HOS (Hours of Service) trip planning application.
It takes trip inputs, calculates routes, simulates FMCSA Hours of Service rules step-by-step,
generates compliant Driver Daily Logs, and displays everything in a clean UI.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + Vite + Tailwind CSS                                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │ TripForm │  │ MapView      │  │ ELDLogViewer      │     │
│  │ (inputs) │  │ (Leaflet)    │  │ (Canvas/SVG grid) │     │
│  └──────────┘  └──────────────┘  └───────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                          │ REST API
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  Django + Django REST Framework                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Routing Svc  │  │ HOS Engine   │  │ Log Generator   │   │
│  │ (ORS API)    │  │ (Simulation) │  │ (ELD Formatter) │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Python 3.11+, Django 5.x, Django REST Framework
- **Frontend**: React 18, Vite, Tailwind CSS, Leaflet.js
- **Routing API**: OpenRouteService (free tier)
- **Map Tiles**: OpenStreetMap via Leaflet
- **Database**: SQLite (dev) / PostgreSQL (prod)

## Deployment Targets

- **Backend**: Render.com or Railway.app
- **Frontend**: Vercel

## Key Files to Deploy

```
eld-trip-planner/
├── backend/                    # Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # Django settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── trips/                  # Main app
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── services/
│       │   ├── routing.py      # OpenRouteService integration
│       │   ├── hos_engine.py   # HOS simulation engine (CRITICAL)
│       │   └── log_generator.py # ELD log generation
│       └── tests/
├── frontend/                   # React project
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── TripForm.jsx
│       │   ├── MapView.jsx
│       │   └── ELDLogSheet.jsx
│       └── services/
│           └── api.js
└── docs/
    └── CONTINUATION_GUIDE.md   # This file
```

## Environment Variables Needed

### Backend (.env)
```
DJANGO_SECRET_KEY=<generate-a-secret-key>
DJANGO_DEBUG=False
ALLOWED_HOSTS=your-backend-domain.com
ORS_API_KEY=<get-from-openrouteservice.org>
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
DATABASE_URL=<postgres-url-for-production>
```

### Frontend (.env)
```
VITE_API_BASE_URL=https://your-backend-domain.com/api
```

## Deployment Steps

### Backend (Render.com)
1. Push backend/ to GitHub
2. Create new Web Service on Render
3. Set build command: `pip install -r requirements.txt && python manage.py migrate`
4. Set start command: `gunicorn config.wsgi:application`
5. Add environment variables
6. Deploy

### Frontend (Vercel)
1. Push frontend/ to GitHub
2. Import project on Vercel
3. Set framework preset to Vite
4. Add VITE_API_BASE_URL env var pointing to backend
5. Deploy

## API Key Setup
- Get free ORS API key at: https://openrouteservice.org/dev/#/signup
- Free tier: 2000 requests/day (sufficient for this app)
