# Deployment Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- OpenRouteService API key (free at https://openrouteservice.org/dev/#/signup)

## Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file
echo "ORS_API_KEY=your_key_here" > .env
echo "DJANGO_DEBUG=True" >> .env

# Run migrations and start server
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

App will be at http://localhost:5173 with API proxied to http://localhost:8000

## Production Deployment

### Backend → Render.com

1. Create a new Web Service on Render
2. Connect your GitHub repo
3. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - **Environment**: Python 3
4. Environment Variables:
   ```
   DJANGO_SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
   DJANGO_DEBUG=False
   ALLOWED_HOSTS=your-app.onrender.com
   ORS_API_KEY=your_openrouteservice_key
   CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
   DATABASE_URL=<provided by Render if using PostgreSQL>
   ```

### Frontend → Vercel

1. Import project from GitHub on Vercel
2. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Environment Variables:
   ```
   VITE_API_BASE_URL=https://your-backend.onrender.com/api
   ```

### Alternative: Railway.app (Backend)

1. Create new project, connect GitHub
2. Add a PostgreSQL database service
3. Add a web service pointing to `backend/`
4. Set environment variables (same as Render)
5. Railway auto-detects Python and runs gunicorn

## PLACEHOLDER Notes for Deploying AI

When deploying this project:
1. Get ORS API key first - it's free, 2000 req/day
2. Backend needs to be deployed BEFORE frontend (frontend needs the URL)
3. Make sure CORS is configured with the exact frontend domain
4. The SQLite database works for demo but use PostgreSQL for production
5. Render free tier spins down after inactivity - first request may be slow
