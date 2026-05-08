# 🚀 ELD Trip Planner - Complete Deployment Guide

## Step 1: Push Code to GitHub

```bash
cd eld-trip-planner
git init
git add .
git commit -m "Initial commit: ELD Trip Planner with route planning and HOS simulation"
git branch -M main
git remote add origin https://github.com/khushikumari1/eld-trip-planner.git
git push -u origin main
```

---

## Step 2: Deploy Backend to Render.com

### 2.1: Create Render Account & Connect GitHub

1. Go to https://render.com and sign up
2. Click **New +** → **Web Service**
3. Select **GitHub** and authorize
4. Search for `eld-trip-planner` repo and click **Connect**

### 2.2: Configure Web Service

- **Name**: `eld-trip-planner-api`
- **Environment**: `Python 3`
- **Root Directory**: `backend`
- **Build Command**:
  ```
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
  ```
- **Start Command**:
  ```
  gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
  ```

### 2.3: Add Environment Variables

Click **Environment** and add these key-value pairs:

| Key                    | Value                                                                                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `DJANGO_SECRET_KEY`    | Generate: run `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_DEBUG`         | `False`                                                                                                                    |
| `ALLOWED_HOSTS`        | `eld-trip-planner-api.onrender.com` (will show during deployment)                                                          |
| `ORS_API_KEY`          | `eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQyMDFkOTQ0ODlhNTQ4NzRhNDc3MzA3MGFiYjRjZGVjIiwiaCI6Im11cm11cjY0In0=` |
| `CORS_ALLOWED_ORIGINS` | (set after Vercel deployment - e.g., `https://eld-trip-planner.vercel.app`)                                                |

### 2.4: Deploy

- Click **Create Web Service**
- Wait for build to complete (5-10 minutes)
- Copy the deployed URL (e.g., `https://eld-trip-planner-api.onrender.com`)

---

## Step 3: Deploy Frontend to Vercel

### 3.1: Import Project

1. Go to https://vercel.com and sign up (or log in)
2. Click **Add New** → **Project**
3. Click **Import Git Repository**
4. Search for `khushikumari1/eld-trip-planner` and click **Import**

### 3.2: Configure Project

- **Root Directory**: `frontend`
- **Framework Preset**: `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

### 3.3: Add Environment Variable

Click **Environment Variables** and add:

| Key                 | Value                                                                              |
| ------------------- | ---------------------------------------------------------------------------------- |
| `VITE_API_BASE_URL` | `https://eld-trip-planner-api.onrender.com/api` (use the Render URL from Step 2.4) |

### 3.4: Deploy

- Click **Deploy**
- Wait for build (2-3 minutes)
- Copy the Vercel URL (e.g., `https://eld-trip-planner.vercel.app`)

---

## Step 4: Update Backend CORS Settings

Go back to Render dashboard:

1. Open `eld-trip-planner-api` service
2. Click **Environment**
3. Update `CORS_ALLOWED_ORIGINS` to your Vercel URL:
   ```
   https://eld-trip-planner.vercel.app
   ```
4. Click **Save Changes** (auto-redeploys)

---

## Step 5: Test Production Deployment

### 5.1: Open Frontend

- Visit your Vercel URL: https://eld-trip-planner.vercel.app

### 5.2: Test a Trip

Fill in the form:

- **Current Location**: `Hyderabad, India`
- **Pickup Location**: `Bangalore, India`
- **Dropoff Location**: `Chennai, India`
- **Current Cycle Used**: `20`

Click **Plan Trip** and verify:

- ✅ Map shows route polyline (blue line)
- ✅ Stop markers appear (colored circles)
- ✅ Summary shows realistic distance and duration
- ✅ ELD Logs tab shows multi-day HOS compliant schedule
- ✅ Each day totals 24 hours

### 5.3: Test Edge Cases

1. **Short trip**: Dallas → Houston (50 mi)
2. **Long trip**: Los Angeles → New York (2500 mi)
3. **High cycle**: Set current_cycle_used to `65`

---

## Troubleshooting

### Backend Deploy Fails

- Check Render build logs for Python errors
- Verify `requirements.txt` has all dependencies
- Ensure `ORS_API_KEY` is set in Environment Variables

### Frontend Deploy Fails

- Check Vercel build logs
- Verify `VITE_API_BASE_URL` is set
- Ensure Node.js version is 18+

### CORS Errors in Production

- Confirm `CORS_ALLOWED_ORIGINS` matches your Vercel domain exactly
- Check DevTools Network tab to see the error
- Backend logs will show the rejected origin

### API Timeouts

- Render free tier may spin down after 15 min inactivity (cold start = slow)
- First request after idle may take 30-60 seconds
- Subsequent requests will be fast

---

## Success Checklist

- ✅ Code pushed to GitHub
- ✅ Backend deployed on Render
- ✅ Frontend deployed on Vercel
- ✅ Environment variables set in both services
- ✅ CORS configured with correct frontend URL
- ✅ Test trip completes successfully
- ✅ Map and ELD logs display correctly
- ✅ Multi-day trips work (cold start delay noted)

---

## URLs After Deployment

| Service         | URL                                                  |
| --------------- | ---------------------------------------------------- |
| **Frontend**    | https://eld-trip-planner.vercel.app                  |
| **Backend API** | https://eld-trip-planner-api.onrender.com/api        |
| **API Docs**    | https://eld-trip-planner-api.onrender.com/api/health |

---

## Next: Record Demo Video

See `docs/LOOM_VIDEO_SCRIPT.md` for a 3-5 minute demo script to share your app.

Good luck! 🎉
