# Setup Guide - Figma-Website UI Comparison Tool

This guide will help you set up and run the project on your local machine.

## System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 2GB free space

## Step-by-Step Setup

### 1. Clone or Download the Project

If you have Git:
```bash
git clone <repository-url>
cd figma-website-diff
```

Or extract the downloaded ZIP file and navigate to the directory.

### 2. Backend Setup

#### Windows

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create environment file
copy .env.example .env

# (Optional) Edit .env file with your preferences using notepad
notepad .env
```

#### macOS/Linux

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers with system dependencies
playwright install --with-deps chromium

# Create environment file
cp .env.example .env

# (Optional) Edit .env file
nano .env
```

### 3. Frontend Setup

Open a **new terminal** window (keep the backend terminal open):

#### Windows/macOS/Linux

```bash
# Navigate to frontend directory from project root
cd frontend

# Install Node dependencies
npm install
```

### 4. Get Figma API Token

1. Go to https://www.figma.com/settings
2. Scroll down to "Personal Access Tokens"
3. Click "Generate new token"
4. Give it a name (e.g., "UI Comparison Tool")
5. Copy the token (you won't be able to see it again!)
6. Save it somewhere safe

## Running the Application

### Option 1: Run Both Servers Manually

You'll need **two terminal windows**:

**Terminal 1 - Backend:**
```bash
cd backend

# Activate virtual environment first
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Run FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend

# Run Vite dev server
npm run dev
```

### Option 2: Docker Compose (Recommended for Production)

Requires Docker Desktop installed.

```bash
# From project root
docker-compose up --build

# To run in background
docker-compose up -d --build
```

## Accessing the Application

Once both servers are running:

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Alternative API Docs**: http://localhost:8000/api/redoc

## Testing the Setup

### 1. Health Check

Open your browser and visit:
```
http://localhost:8000/api/v1/health
```

You should see:
```json
{
  "status": "healthy",
  "service": "figma-website-diff",
  "version": "1.0.0"
}
```

### 2. Test Comparison

1. Open http://localhost:5173
2. Enter test values:
   - **Figma URL**: Any public Figma file URL
   - **Figma Token**: Your API token
   - **Website URL**: Any public website (e.g., https://example.com)
3. Click "Start Comparison"
4. Watch the progress bar
5. View the results!

## Common Issues & Solutions

### Issue: "playwright: command not found"

**Solution:**
```bash
# Make sure you're in the virtual environment
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Then install
playwright install chromium
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find and kill the process (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Find and kill the process (macOS/Linux)
lsof -i :8000
kill -9 <PID>

# Or change the port in backend/app/main.py
```

### Issue: "Module not found" errors in frontend

**Solution:**
```bash
cd frontend

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Issue: Figma API returns 403 Forbidden

**Causes:**
- Invalid token
- Token doesn't have access to the file
- File is private and not shared

**Solution:**
- Verify your token is correct
- Make sure the Figma file is publicly accessible OR
- Your token account has access to the file

### Issue: Website comparison fails

**Causes:**
- Website blocks bots (Cloudflare, etc.)
- Website requires authentication
- JavaScript-heavy site needs more time to load

**Solution:**
- Try a different website first
- Increase `PLAYWRIGHT_TIMEOUT` in `.env`
- Add `wait_for_selector` in advanced settings

### Issue: Comparison is very slow

**Solutions:**
- Reduce viewport size
- Use smaller Figma frames
- Check your internet connection
- Close other heavy applications

## Development Tips

### Hot Reloading

- **Backend**: Changes to Python files automatically reload
- **Frontend**: Changes to React files update instantly

### Debugging

**Backend:**
```bash
# Enable debug logging
# In .env file:
DEBUG=True

# View logs in terminal
```

**Frontend:**
```bash
# Open browser console (F12)
# View network requests and errors
```

### Running Tests

```bash
# Backend tests (if available)
cd backend
pytest

# Frontend tests (if available)
cd frontend
npm test
```

## Environment Variables Reference

### Backend (.env)

```env
# Required
API_V1_PREFIX=/api/v1

# Optional
DEBUG=True
COLOR_TOLERANCE=5
SPACING_TOLERANCE=2
PLAYWRIGHT_TIMEOUT=30000
DEFAULT_VIEWPORT_WIDTH=1920
DEFAULT_VIEWPORT_HEIGHT=1080
```

## Next Steps

1. ✅ Setup complete!
2. 📖 Read the [README.md](README.md) for usage instructions
3. 🎨 Try your first comparison
4. 📊 Explore the API docs at http://localhost:8000/api/docs
5. 🚀 Deploy to production (see Deployment section in README)

## Getting Help

If you encounter issues not covered here:

1. Check the console/terminal for error messages
2. Review the [Troubleshooting](#common-issues--solutions) section
3. Check browser console (F12) for frontend errors
4. Verify all prerequisites are installed
5. Try restarting both servers

## Production Deployment

For deploying to production:

1. Set `DEBUG=False` in backend `.env`
2. Build frontend: `npm run build`
3. Use a production WSGI server (Gunicorn/Uvicorn)
4. Set up HTTPS
5. Configure proper CORS settings
6. Use Redis for caching (optional)
7. Set up monitoring

---

**Happy Comparing! 🎨✨**
