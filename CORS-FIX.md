# CORS Fix Instructions

## The Problem
CORS errors occur because the backend server needs to be restarted after the CORS configuration change.

## Solution: Restart Backend Server

### Step 1: Stop the Current Server
In the terminal where `uvicorn` is running:
- Press `Ctrl+C` to stop the server

### Step 2: Restart the Server
```bash
uvicorn app.web:app --reload --host 0.0.0.0 --port 8000
```

**IMPORTANT**: Even though `--reload` should auto-reload, CORS middleware changes sometimes require a full restart.

### Step 3: Verify CORS is Working
Open a new terminal and test:
```bash
# Test from PowerShell
Invoke-WebRequest -Uri "http://localhost:8000/api/health" -Headers @{"Origin"="http://localhost:3000"} | Select-Object -ExpandProperty Headers
```

You should see `Access-Control-Allow-Origin` in the headers.

### Step 4: Refresh Browser
- Go to `http://localhost:3000`
- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Check browser console (F12) - CORS errors should be gone

## Alternative: Use Vite Proxy (If CORS Still Fails)

If CORS still doesn't work, the frontend is already configured to proxy API calls through Vite. The proxy is set up in `frontend/vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

This means the frontend should be making requests to `/api/events` (relative URL) instead of `http://localhost:8000/api/events`. Let me check if the API client is using the correct URL.

