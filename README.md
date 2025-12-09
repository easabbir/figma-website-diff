# 🎨 Figma ↔ Website UI Comparison Tool

A powerful Python + FastAPI tool that compares Figma designs with live websites to detect visual and UI inconsistencies. Features a modern React frontend with real-time progress updates, user authentication, and elegant UI design.

![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Table of Contents

- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [Detailed Setup Guide](#-detailed-setup-guide)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Docker Setup](#-docker-setup)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🆕 What's New (v1.4.0)

### Latest Features
- ✅ **Redis Job Storage** - Persistent job state with automatic fallback to in-memory
- ✅ **Email OTP Verification** - Secure signup with 6-digit email verification
- ✅ **Figma OAuth Integration** - Connect with Figma OAuth for seamless authentication
- ✅ **PDF Export** - Download professional PDF reports
- ✅ **Comparison History** - View and manage past comparisons with SQLite storage
- ✅ **Responsive Mode** - Compare designs across multiple viewports

## ✨ Features

| Category | Features |
|----------|----------|
| **🎯 Comparison** | Color analysis, Typography, Layout & spacing, Dimensions, Pixel-perfect visual diff |
| **🚀 Architecture** | FastAPI backend, React + TailwindCSS frontend, WebSocket progress, Redis job storage |
| **📊 Reports** | JSON, HTML, PDF exports, Interactive slider comparison |
| **🔐 Security** | JWT auth, Email OTP verification, Figma OAuth, User-specific history |

## 💻 System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11 - 3.13 | 3.14 not yet supported |
| **Node.js** | 18+ | With npm |
| **Redis** | 6+ | Optional (falls back to in-memory) |
| **OS** | Windows, macOS, Linux | All platforms supported |

## 🚀 Quick Start

### One-Command Setup (macOS/Linux)

```bash
# Clone and setup everything
git clone <your-repo-url> figma-website-diff
cd figma-website-diff

# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000 &

# Frontend (new terminal)
cd ../frontend
npm install && npm run dev
```

**Access the app at:** http://localhost:5173

---

## 📖 Detailed Setup Guide

### Step 1: Clone the Repository

```bash
git clone <your-repo-url> figma-website-diff
cd figma-website-diff
```

### Step 2: Backend Setup

#### Windows
```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1
# OR (Command Prompt)
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Copy environment file
copy .env.example .env

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### macOS
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (with system deps)
playwright install chromium

# Copy environment file
cp .env.example .env

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Linux (Ubuntu/Debian)
```bash
cd backend

# Install system dependencies (if needed)
sudo apt update
sudo apt install python3-venv python3-pip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser with system dependencies
playwright install --with-deps chromium

# Copy environment file
cp .env.example .env

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Frontend Setup (All Platforms)

```bash
# Open a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Step 4: (Optional) Redis Setup

Redis enables persistent job storage across server restarts.

#### macOS (Homebrew)
```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

#### Windows
```powershell
# Using Docker (recommended)
docker run -d -p 6379:6379 --name redis redis:alpine

# Or download from https://github.com/microsoftarchive/redis/releases
```

#### Docker (All Platforms)
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

> **Note:** If Redis is not available, the app automatically falls back to in-memory storage.

---

## 🐳 Docker Setup

### Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build

# Stop services
docker-compose down
```

### Access Points
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/api/docs |

---

## 🛠️ Configuration

### Backend Environment Variables (`backend/.env`)

Copy `.env.example` to `.env` and configure:

```env
# ===========================================
# APPLICATION SETTINGS
# ===========================================
APP_NAME=Figma-Website UI Comparison Tool
APP_VERSION=1.0.0
DEBUG=True

# ===========================================
# API SETTINGS
# ===========================================
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# ===========================================
# FILE STORAGE
# ===========================================
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
STATIC_DIR=static
MAX_UPLOAD_SIZE=52428800  # 50MB

# ===========================================
# FIGMA API
# ===========================================
FIGMA_API_BASE_URL=https://api.figma.com/v1
FIGMA_DEFAULT_SCALE=2

# Figma OAuth 2.0 (Create app at https://www.figma.com/developers/apps)
FIGMA_CLIENT_ID=your_client_id_here
FIGMA_CLIENT_SECRET=your_client_secret_here
FIGMA_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback

# ===========================================
# WEBSITE CAPTURE (Playwright)
# ===========================================
PLAYWRIGHT_TIMEOUT=30000
DEFAULT_VIEWPORT_WIDTH=1920
DEFAULT_VIEWPORT_HEIGHT=1080

# ===========================================
# COMPARISON SETTINGS
# ===========================================
COLOR_TOLERANCE=5        # Delta E (0-100)
SPACING_TOLERANCE=2      # Pixels
PIXEL_DIFF_THRESHOLD=0.95

# ===========================================
# REDIS (Job State Persistence)
# ===========================================
# Falls back to in-memory if Redis unavailable
REDIS_URL=redis://localhost:6379/0

# ===========================================
# EMAIL (OTP Verification)
# ===========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=UI Diff Checker
```

### Figma OAuth Setup

1. Go to [Figma Developers](https://www.figma.com/developers/apps)
2. Click "Create a new app"
3. Fill in app details:
   - **App name**: Your app name
   - **Website URL**: `http://localhost:5173`
   - **Callback URL**: `http://localhost:8000/api/v1/oauth/callback`
4. Copy **Client ID** and **Client Secret** to your `.env` file

### Email Setup (Gmail)

1. Enable 2-Factor Authentication on your Google account
2. Go to: Google Account → Security → App Passwords
3. Generate a new app password for "Mail"
4. Use the 16-character password as `SMTP_PASSWORD`

> **Dev Mode:** If SMTP is not configured, OTP codes are logged to console.

---

## 📖 Usage

### 1. Create an Account
- Open http://localhost:5173
- Click "Sign Up"
- Enter email and password
- Verify with OTP code (check email or console logs)

### 2. Get Figma Access

**Option A: OAuth (Recommended)**
- Click "Connect Figma" in the app
- Authorize with your Figma account
- Token is automatically saved

**Option B: Personal Access Token**
- Go to [Figma Settings](https://www.figma.com/settings)
- Generate a Personal Access Token
- Paste it in the comparison form

### 3. Run a Comparison
1. Enter Figma file URL (supports `/file/` and `/design/` formats)
2. Enter website URL
3. Click "Start Comparison"
4. View results with interactive slider

### 4. Export Reports
- **HTML Report**: View in browser
- **PDF Report**: Download for sharing

---

## 📡 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/compare` | Start a comparison job |
| `GET` | `/api/v1/report/{job_id}` | Get comparison report |
| `GET` | `/api/v1/progress/{job_id}` | Get job progress |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/report/{job_id}/pdf` | Download PDF report |
| `GET` | `/api/v1/history` | Get comparison history |
| `POST` | `/api/v1/auth/login` | User login |
| `POST` | `/api/v1/auth/signup/request-otp` | Request signup OTP |
| `GET` | `/api/v1/oauth/authorize` | Start Figma OAuth |

### API Example

```python
import requests

# Login
auth = requests.post('http://localhost:8000/api/v1/auth/login', json={
    "email": "user@example.com",
    "password": "password123"
})
token = auth.json()['access_token']
headers = {"Authorization": f"Bearer {token}"}

# Start comparison
response = requests.post(
    'http://localhost:8000/api/v1/compare',
    headers=headers,
    json={
        "figma_input": {
            "type": "url",
            "value": "https://www.figma.com/design/ABC123/Design",
            "access_token": "your-figma-token"
        },
        "website_url": "https://example.com",
        "options": {
            "viewport": {"width": 1920, "height": 1080},
            "comparison_mode": "hybrid"
        }
    }
)

job_id = response.json()['job_id']

# Poll for completion
import time
while True:
    progress = requests.get(f'http://localhost:8000/api/v1/progress/{job_id}')
    status = progress.json()['status']
    if status in ['completed', 'failed']:
        break
    time.sleep(2)

# Get report
report = requests.get(f'http://localhost:8000/api/v1/report/{job_id}')
print(f"Match Score: {report.json()['summary']['match_score']}%")
```

### Interactive API Docs

Visit http://localhost:8000/api/docs for Swagger UI documentation.

## 📁 Project Structure

```
figma-website-diff/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py         # REST API routes
│   │   │   ├── auth_endpoints.py    # Authentication routes
│   │   │   └── websocket.py         # WebSocket for progress
│   │   ├── services/
│   │   │   ├── figma_extractor.py   # Figma API client
│   │   │   ├── figma_oauth.py       # Figma OAuth handler
│   │   │   ├── web_analyzer.py      # Playwright website capture
│   │   │   ├── comparator.py        # Comparison engine
│   │   │   ├── job_storage.py       # Redis/in-memory job storage
│   │   │   ├── database.py          # SQLite history storage
│   │   │   └── report_generator.py  # Report generation
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic models
│   │   ├── config.py                # Configuration
│   │   └── main.py                  # FastAPI app
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ComparisonForm.tsx   # Input form
│   │   │   ├── ReportDisplay.tsx    # Results view
│   │   │   ├── HistoryModal.tsx     # History viewer
│   │   │   └── AuthPage.tsx         # Login/Signup
│   │   ├── context/
│   │   │   └── AuthContext.tsx      # Auth state management
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
└── README.md
```

---

## 🚨 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Port 8000 in use** | `lsof -ti:8000 \| xargs kill -9` (macOS/Linux) or change port |
| **Port 5173 in use** | `lsof -ti:5173 \| xargs kill -9` (macOS/Linux) or change port |
| **Playwright fails** | Run `playwright install --with-deps chromium` |
| **Redis connection refused** | Install Redis or ignore (falls back to in-memory) |
| **Python 3.14 errors** | Use Python 3.11-3.13 instead |

### Playwright Installation

```bash
# Windows
playwright install chromium

# macOS
playwright install chromium

# Linux (with system dependencies)
playwright install --with-deps chromium
```

### Figma API Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid token | Regenerate token or re-authenticate OAuth |
| 403 Forbidden | No file access | Ensure token has access to the file |
| 429 Rate Limited | Too many requests | Wait 1-2 minutes and retry |
| Invalid URL | Wrong URL format | Use `figma.com/file/...` or `figma.com/design/...` |

### Email/OTP Issues

- **OTP not received**: Check spam folder or backend console logs
- **SMTP error**: Verify Gmail app password (not regular password)
- **Dev mode**: OTP codes are printed to console when SMTP is not configured

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

| Technology | Purpose |
|------------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | Backend framework |
| [React](https://react.dev/) | Frontend library |
| [Playwright](https://playwright.dev/) | Browser automation |
| [TailwindCSS](https://tailwindcss.com/) | Styling |
| [Redis](https://redis.io/) | Job state persistence |
| [Figma API](https://www.figma.com/developers/) | Design data access |

---

**Made with ❤️ for designers and developers**
