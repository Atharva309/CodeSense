# Quick Start - Run CloudSense Locally

## The Problem
You're seeing the old UI because you're accessing `http://localhost:8000` (the backend). The new React UI runs on `http://localhost:3000`.

## Solution: Run These Commands

### Terminal 1: Backend (FastAPI)
```bash
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense"
uvicorn app.web:app --reload --host 0.0.0.0 --port 8000
```

**Verify**: Open `http://localhost:8000/api/health` in browser - should show `{"ok":true,"env":"dev"}`

### Terminal 2: Frontend (React)
```bash
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense\frontend"
npm run dev
```

**Verify**: Should show `Local: http://localhost:3000/`

### Terminal 3: Redis (for background jobs)
```bash
docker run -d -p 6379:6379 redis:7
```

### Terminal 4: Worker (optional, processes reviews)
```bash
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense"
rq worker reviews
```

### Terminal 5: ngrok (for GitHub webhooks)
```bash
ngrok http 8000
```

## Access the Application

**Open your browser and go to:**
```
http://localhost:3000
```

**NOT** `http://localhost:8000` ← This is the old HTML UI

## What You Should See

1. **Dashboard** (`http://localhost:3000/`):
   - Modern UI with dark mode toggle
   - Stats cards
   - Recent events list

2. **Events Page** (`http://localhost:3000/events`):
   - Modern table with pagination
   - Clickable rows
   - Status badges

3. **Event Detail** (click any event):
   - Event information
   - "Run Review" button
   - List of reviews

4. **Review Detail** (click any review):
   - Findings grouped by file
   - Syntax highlighted code
   - Patch viewer

## Troubleshooting

### "Cannot connect to API" error
1. Check backend is running: `curl http://localhost:8000/api/health`
2. Check browser console (F12) for errors
3. Verify CORS is enabled in `app/web.py`

### Still seeing old UI
- Make sure you're on `http://localhost:3000` not `http://localhost:8000`
- Clear browser cache (Ctrl+Shift+R)
- Check Terminal 2 shows Vite is running

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend errors
```bash
# Check if all dependencies are installed
pip install -r requirements.txt

# Check if database exists
ls cloudsense.db
```

## Testing API Directly

Test the new API endpoints:
```bash
# Health check
curl http://localhost:8000/api/health

# List events
curl http://localhost:8000/api/events

# Get event detail
curl http://localhost:8000/api/events/1

# Get review detail
curl http://localhost:8000/api/reviews/1
```

## Ports Summary

- **3000**: Frontend (React) - **USE THIS FOR THE NEW UI**
- **8000**: Backend (FastAPI) - API endpoints at `/api/*`
- **6379**: Redis (for background jobs)
- **ngrok**: Exposes port 8000 for GitHub webhooks

