# Local Development Guide

## Quick Start

### Step 1: Start Backend (FastAPI)

Open Terminal 1:
```bash
# Navigate to project root
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense"

# Activate virtual environment (if you have one)
# .venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the FastAPI backend
uvicorn app.web:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 2: Start Frontend (React + Vite)

Open Terminal 2:
```bash
# Navigate to frontend directory
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense\frontend"

# Install dependencies (if not already done)
npm install

# Start the development server
npm run dev
```

You should see:
```
  VITE v7.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### Step 3: Access the Application

**IMPORTANT**: Open your browser and go to:
```
http://localhost:3000
```

**NOT** `http://localhost:8000` (that's the old HTML UI)

The new React UI runs on port 3000 and will automatically proxy API calls to the backend on port 8000.

### Step 4: Start Redis (for background jobs)

Open Terminal 3:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7

# OR using docker-compose (from project root)
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense"
docker-compose up redis -d
```

### Step 5: Start Worker (optional, for processing reviews)

Open Terminal 4:
```bash
# Navigate to project root
cd "S:\CU BOULDER\SEMESTER-3\DataScaleComputing\cloudsense"

# Activate virtual environment
# .venv\Scripts\activate  # Windows

# Set environment variables (create .env file if needed)
# REDIS_HOST=localhost
# REDIS_PORT=6379

# Start the worker
rq worker reviews
```

### Step 6: Expose with ngrok (for GitHub webhooks)

Open Terminal 5:
```bash
# Expose backend (port 8000) for GitHub webhooks
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://xxxx.ngrok.io`) and use it in your GitHub webhook configuration:
- Payload URL: `https://xxxx.ngrok.io/webhook`
- Content type: `application/json`
- Secret: (your `GH_WEBHOOK_SECRET`)

## Troubleshooting

### Frontend shows "Cannot connect to API"
1. Make sure backend is running on port 8000
2. Check browser console for errors
3. Verify `http://localhost:8000/api/health` returns `{"ok": true, "env": "dev"}`

### Frontend shows old UI
- Make sure you're accessing `http://localhost:3000` NOT `http://localhost:8000`
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check that `npm run dev` is running in the frontend directory

### API calls fail
1. Check CORS is enabled in `app/web.py`
2. Verify the API router is included: `app.include_router(api_router)`
3. Test API directly: `curl http://localhost:8000/api/health`

### Port already in use
- Backend (8000): Change port in uvicorn command or kill existing process
- Frontend (3000): Vite will automatically try next available port

## Environment Variables

Create a `.env` file in the project root:

```env
# GitHub
GITHUB_TOKEN=your_github_token
GH_WEBHOOK_SECRET=your_webhook_secret

# OpenAI (optional, for AI reviews)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Database
DB_PATH=cloudsense.db

# App
APP_ENV=dev
PUBLIC_WEBHOOK_BASE=http://localhost:8000
```

## Testing the New UI

1. **Dashboard**: Go to `http://localhost:3000/` - should show stats and recent events
2. **Events**: Go to `http://localhost:3000/events` - should show a modern table with events
3. **Event Detail**: Click on any event - should show event details and reviews
4. **Review Detail**: Click on a review - should show findings with syntax highlighting

## What Changed

- **Old UI**: HTML pages served directly from FastAPI at `http://localhost:8000`
- **New UI**: React SPA served by Vite at `http://localhost:3000`
- **API**: JSON endpoints at `http://localhost:8000/api/*`
- **Old HTML endpoints**: Still available at `http://localhost:8000/events`, `/reviews`, etc. (for backward compatibility)

