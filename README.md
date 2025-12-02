# 🎨 Figma ↔ Website UI Comparison Tool

A powerful Python + FastAPI tool that compares Figma designs with live websites to detect visual and UI inconsistencies. Features a modern React frontend with real-time progress updates, user authentication, and elegant UI design.

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)

## 🆕 Recent Updates (v1.2.0)

### New Features
- ✅ **User Authentication** - Secure login/signup with JWT tokens
- ✅ **User-Specific History** - Each user can only view their own comparison history
- ✅ **Figma OAuth Integration** - Connect with Figma OAuth for seamless authentication
- ✅ **Modern UI Design** - Elegant violet/purple gradient theme with glassmorphism effects
- ✅ **Improved Error Handling** - Meaningful error messages for rate limits, auth errors, and more
- ✅ **Password Visibility Toggle** - Show/hide password in login forms
- ✅ **Delete All History** - Bulk delete comparison history with confirmation
- ✅ **Form State Management** - Form clears on login/logout for better UX

### UI Improvements
- ✅ **Redesigned Auth Page** - Beautiful gradient background with floating orbs and feature cards
- ✅ **Redesigned Comparison Form** - Modern styling with gradient buttons and improved layout
- ✅ **Redesigned History Modal** - Consistent violet theme with stat cards and search functionality
- ✅ **Scroll Lock on Modals** - Background doesn't scroll when modals are open

### Previous Updates (v1.1.0)
- ✅ **PDF Export** - Download professional PDF reports with executive summary and visual comparisons
- ✅ **Comparison History** - View and manage past comparisons with SQLite storage
- ✅ **Responsive Mode** - Compare designs across multiple viewports (mobile, tablet, desktop) in one run
- ✅ **History Dashboard** - Statistics, filtering, and quick access to past reports

### Bug Fixes (v1.0.2)
- ✅ **Fixed white screen crash** - Replaced incompatible image comparison library with React 18 compatible version
- ✅ **Added ErrorBoundary** - Graceful error handling instead of white screens
- ✅ **Fixed race condition** - Report now loads correctly without "Invalid Report Data" error
- ✅ **Form input caching** - Your inputs are preserved when navigating back from results
- ✅ **Figma URL support** - Now supports both `/file/` and `/design/` URL formats
- ✅ **Better error handling** - Clear messages for rate limits and API errors
- ✅ **Screenshot URLs fixed** - Visual comparison slider now works properly
- ✅ **Improved polling** - More efficient progress tracking without premature fetches

## ✨ Features

- **🎯 Multi-Layer Comparison**
  - Color analysis with perceptual difference detection
  - Typography comparison (fonts, sizes, weights)
  - Layout & spacing analysis
  - Dimension checking
  - Pixel-perfect visual diff

- **🚀 Modern Architecture**
  - FastAPI backend with async support
  - React frontend with TailwindCSS
  - Real-time WebSocket progress updates
  - RESTful API design

- **📊 Comprehensive Reports**
  - JSON output for CI/CD integration
  - Beautiful HTML reports
  - Side-by-side visual comparison with interactive slider
  - Categorized differences (Critical/Warning/Info)

- **💻 User-Friendly Interface**
  - Modern violet/purple gradient design
  - Secure user authentication (login/signup)
  - Interactive diff viewer with slider
  - Real-time progress bar
  - Filter and search differences
  - **Form input caching** - preserves your inputs when navigating back
  - Supports both `/file/` and `/design/` Figma URL formats

- **🔐 Security & Privacy**
  - JWT-based authentication
  - User-specific comparison history
  - Figma OAuth integration
  - Password visibility toggle
  - Secure token storage

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         React Frontend (Vite)           │
│   TailwindCSS + shadcn/ui + Lucide     │
└───────────────┬─────────────────────────┘
                │ HTTP/WebSocket
┌───────────────▼─────────────────────────┐
│         FastAPI Backend                  │
│  ┌──────────────┬──────────────┐       │
│  │Figma API     │Playwright    │       │
│  │Extractor     │Web Analyzer  │       │
│  └──────┬───────┴───────┬──────┘       │
│         │               │               │
│  ┌──────▼───────────────▼──────┐       │
│  │   Comparison Engine          │       │
│  │  - Color Analysis            │       │
│  │  - Layout Comparison         │       │
│  │  - Visual Diff               │       │
│  └──────────────┬───────────────┘       │
│                 │                        │
│  ┌──────────────▼───────────────┐       │
│  │   Report Generator           │       │
│  │  - JSON + HTML + Visual      │       │
│  └──────────────────────────────┘       │
└─────────────────────────────────────────┘
```

## 📋 Prerequisites

- **Python** 3.13+ (3.14 not yet supported due to package compatibility)
- **Node.js** 18+ and npm
- **Figma API Token** ([Get here](https://www.figma.com/developers/api#access-tokens))
- **Git** (optional)

> ⚠️ **Note**: Python 3.14 is not currently supported. Use Python 3.13.7 or earlier.

## 🚀 Quick Start

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment file
copy .env.example .env

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## 🐳 Docker Setup (Alternative)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

## 📖 Usage

### 1. **Create an Account**
   - Open the web interface at `http://localhost:5173`
   - Click "Sign Up" to create a new account
   - Enter your email and password
   - You'll be redirected to the comparison dashboard

### 2. **Get Figma API Token** (Choose one method)
   
   **Option A: Personal Access Token**
   - Go to [Figma Settings](https://www.figma.com/settings)
   - Scroll to "Personal Access Tokens"
   - Click "Generate new token"
   - Copy and save the token
   
   **Option B: Figma OAuth (Recommended)**
   - Click "Connect Figma" in the comparison form
   - Authorize the app in Figma
   - Your token will be automatically saved

### 3. **Start a Comparison**
   - Enter your Figma file URL
   - Paste your Figma API token (or use OAuth)
   - Enter the website URL to compare
   - Click "Start Comparison"

### 4. **View Results**
   - Monitor real-time progress
   - View overall match score
   - Explore categorized differences
   - Download HTML or PDF report
   - View comparison history (your comparisons only)

### API Usage Example

```python
import requests

# Start comparison
response = requests.post('http://localhost:8000/api/v1/compare', json={
    "figma_input": {
        "type": "url",
        # Supports both /file/ and /design/ URL formats
        "value": "https://www.figma.com/design/ABC123/Design",
        "access_token": "your-figma-token"
    },
    "website_url": "https://example.com",
    "options": {
        "viewport": {"width": 1920, "height": 1080},
        "comparison_mode": "hybrid",
        "tolerance": {
            "color": 5,
            "spacing": 2
        }
    }
})

job_id = response.json()['job_id']

# Check progress
progress = requests.get(f'http://localhost:8000/api/v1/progress/{job_id}')

# Get report
report = requests.get(f'http://localhost:8000/api/v1/report/{job_id}')
```

## 📊 Comparison Methods

### 1. **Structural Comparison**
- Extracts design tokens from Figma API
- Analyzes DOM structure and computed styles
- Compares:
  - Color palettes (with Delta E tolerance)
  - Font families, sizes, weights
  - Spacing & padding
  - Element dimensions
  - Layout alignment

### 2. **Visual Comparison**
- Screenshot-based pixel diff
- Structural Similarity Index (SSIM)
- Perceptual hashing
- Highlights visual mismatches

### 3. **Hybrid Mode** (Recommended)
- Combines both structural and visual analysis
- Most accurate results
- Provides detailed insights

## 🛠️ Configuration

### Backend Configuration (`backend/.env`)

```env
# API Settings
API_V1_PREFIX=/api/v1
DEBUG=True

# File Storage
OUTPUT_DIR=outputs
MAX_UPLOAD_SIZE=52428800

# Comparison Tolerances
COLOR_TOLERANCE=5
SPACING_TOLERANCE=2
PIXEL_DIFF_THRESHOLD=0.95

# Playwright
PLAYWRIGHT_TIMEOUT=30000
DEFAULT_VIEWPORT_WIDTH=1920
DEFAULT_VIEWPORT_HEIGHT=1080
```

### Tolerance Guidelines

- **Color Tolerance** (0-100): Delta E color difference threshold
  - 0-5: Very strict (identical colors)
  - 5-10: Strict (barely noticeable)
  - 10-20: Moderate (noticeable difference)

- **Spacing Tolerance** (pixels): Acceptable spacing variation
  - 0-2: Pixel-perfect
  - 2-5: Tight tolerance
  - 5+: Loose tolerance

## 📁 Project Structure

```
figma-website-diff/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py      # REST API routes
│   │   │   └── websocket.py      # WebSocket for progress
│   │   ├── services/
│   │   │   ├── figma_extractor.py   # Figma API client
│   │   │   ├── web_analyzer.py      # Playwright website capture
│   │   │   ├── comparator.py        # Comparison engine
│   │   │   └── report_generator.py  # Report generation
│   │   ├── utils/
│   │   │   ├── color_utils.py    # Color analysis utilities
│   │   │   ├── layout_utils.py   # Layout comparison
│   │   │   └── image_utils.py    # Image processing
│   │   ├── models/
│   │   │   └── schemas.py        # Pydantic models
│   │   ├── config.py             # Configuration
│   │   └── main.py               # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ComparisonForm.tsx   # Input form
│   │   │   ├── ReportDisplay.tsx    # Results view
│   │   │   ├── DiffViewer.tsx       # Difference viewer
│   │   │   └── Header.tsx           # App header
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
└── README.md
```

## 🎯 Roadmap

- [ ] **Figma Plugin** for direct export
- [ ] **CI/CD Integration** (GitHub Actions, GitLab CI)
- [ ] **AI-Powered Semantic Comparison** (CLIP model)
- [ ] **Component-Level Matching** (intelligent element pairing)
- [ ] **Accessibility Audit** (WCAG compliance check)
- [ ] **Multi-Page Comparison**
- [ ] **Historical Tracking** (track changes over time)
- [ ] **Slack/Discord Notifications**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework
- **Playwright** - Browser automation
- **React** - Frontend library
- **TailwindCSS** - Utility-first CSS
- **Figma API** - Design data access
- **scikit-image** - Image processing

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/figma-website-diff/issues)
- **Documentation**: [API Docs](http://localhost:8000/api/docs)

## ⚠️ Limitations

- Requires Figma API token (free tier available)
- Website must be publicly accessible or allow bot access
- JavaScript-heavy sites may need additional wait time
- Large designs may take longer to process
- Comparison accuracy depends on design structure

## 🚨 Troubleshooting

### Playwright Installation Issues
```bash
# Windows
playwright install chromium

# macOS/Linux with system dependencies
playwright install --with-deps chromium
```

### Port Already in Use
```bash
# Change port in backend/app/main.py
# Or frontend/vite.config.ts
```

### Figma API Errors
- Verify token is valid
- Check file URL is correct (supports both `/file/` and `/design/` formats)
- Ensure file has public link access or token has access
- **Rate Limit (429 Error)**: Personal tokens are limited to 2 requests per minute. Wait 1-2 minutes and retry.

### Python Version Issues
```bash
# If you encounter package build errors, ensure you're using Python 3.13 or earlier
python --version  # Should show 3.13.x or earlier

# Create a new virtual environment with the correct Python version
python3.13 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### "Invalid Report Data" or White Screen
If you see "Invalid Report Data" or a white screen after comparison:
- **Cause**: Race condition or incompatible React library (react-compare-image)
- **Fixed in v1.0.2**: 
  - Replaced `react-compare-image` with `react-compare-slider` (React 18 compatible)
  - Added ErrorBoundary to catch and display errors gracefully
  - Fixed report fetching to wait for completion
- **Solution**: Update to the latest version and refresh the page. The issue is resolved.

### Comparison Takes Too Long
- Large Figma files may take 30-60 seconds to process
- Complex websites with many elements take longer to analyze
- Visual comparison (pixel diff) is the most time-intensive step
- Check the progress bar for real-time status updates

---

**Made with ❤️ for designers and developers**
