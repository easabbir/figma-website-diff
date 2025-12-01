# Figma-Website UI Comparison Tool

## Overview
This is a full-stack web application that automatically compares Figma designs with live websites to detect visual inconsistencies between design and implementation.

---

## Tech Stack

### Backend (Python/FastAPI)
- **FastAPI** - Modern async Python web framework for REST APIs
- **Playwright** - Browser automation for capturing website screenshots
- **ReportLab** - PDF report generation
- **Pillow (PIL)** - Image processing and comparison
- **SQLite** - Lightweight database for comparison history
- **Pydantic** - Data validation and settings management

### Frontend (React/TypeScript)
- **React 18** with TypeScript
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Axios** - HTTP client for API calls
- **React-Toastify** - Toast notifications
- **React-Compare-Slider** - Visual side-by-side comparison
- **Lucide React** - Icon library

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Frontend │────▶│  FastAPI Backend │────▶│   Figma API     │
│   (Port 5173)    │     │   (Port 8000)    │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Playwright    │
                        │ (Website Capture)│
                        └─────────────────┘
```

---

## Key Features & How They Work

### 1. Figma Design Extraction
**Component:** `FigmaExtractor` class → Figma REST API

- Extracts design data using Figma's REST API
- Supports both **Personal Access Tokens** and **OAuth 2.0** authentication
- Uses `/files/{key}/nodes` endpoint for specific frames (faster for large files)
- Caches API responses for 30 minutes to reduce API calls
- Exports design as PNG images for visual comparison

### 2. Website Capture
**Component:** Playwright → Headless Chromium → Screenshot

- Uses Playwright to launch a headless browser
- Captures full-page screenshots at specified viewport sizes
- Extracts computed CSS styles from DOM elements
- Supports custom wait conditions for dynamic content

### 3. Comparison Engine
**Component:** `UIComparator` class → Structural + Visual comparison

- **Structural comparison**: Compares extracted design tokens (colors, typography, spacing)
- **Visual comparison**: Pixel-by-pixel image diff using PIL
- **Hybrid mode**: Combines both approaches
- Calculates **match score** (0-100%) based on differences found

### 4. Difference Detection
Detects these types of differences:
- **Color** - Background, text, border colors
- **Typography** - Font family, size, weight, line-height
- **Spacing** - Margins, padding, gaps
- **Dimensions** - Width, height mismatches
- **Layout** - Position, alignment issues
- **Missing/Extra elements**

### 5. Report Generation
- **HTML Report** - Interactive web-based report
- **PDF Report** - Professional document with:
  - Executive summary with match score
  - Visual comparison screenshots
  - Detailed differences with element names and coordinates
  - Severity levels (Critical, Warning, Info)

### 6. OAuth 2.0 Integration
**Flow:** Frontend → Backend → Figma OAuth → Token Storage

- Implements Figma OAuth 2.0 flow for higher API rate limits
- Stores tokens securely (file-based, can be upgraded to database)
- Supports token refresh

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/compare` | POST | Start a new comparison job |
| `/api/v1/progress/{job_id}` | GET | Get job progress (polling) |
| `/api/v1/report/{job_id}` | GET | Get comparison results |
| `/api/v1/history` | GET | List past comparisons |
| `/api/v1/oauth/authorize` | GET | Get Figma OAuth URL |
| `/api/v1/oauth/callback` | GET | OAuth callback handler |
| `/api/v1/oauth/status` | GET | Check OAuth status |

---

## Data Flow

1. **User submits** Figma URL + Website URL + Token
2. **Backend creates job** and returns job ID
3. **Frontend polls** `/progress/{job_id}` for updates
4. **Backend extracts** Figma design data via API
5. **Backend captures** website screenshot via Playwright
6. **Comparison engine** analyzes both and finds differences
7. **Reports generated** (HTML + PDF)
8. **Results returned** to frontend with match score and differences

---

## Project Structure

```
figma-website-diff/
├── backend/
│   ├── app/
│   │   ├── api/endpoints.py         # REST API routes
│   │   ├── config.py                # App configuration
│   │   ├── models/schemas.py        # Pydantic models
│   │   └── services/
│   │       ├── figma_extractor.py   # Figma API integration
│   │       ├── figma_oauth.py       # OAuth 2.0 handling
│   │       ├── website_analyzer.py  # Playwright capture
│   │       ├── ui_comparator.py     # Comparison logic
│   │       └── pdf_generator.py     # PDF reports
│   ├── data/                        # SQLite DB, tokens
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ComparisonForm.tsx   # Input form
│   │   │   ├── ReportDisplay.tsx    # Results view
│   │   │   ├── FigmaOAuth.tsx       # OAuth UI
│   │   │   └── DiffViewer.tsx       # Diff visualization
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
```

---

## Key Technical Decisions

1. **Async job processing** - Long comparisons run in background, frontend polls for progress
2. **Caching** - Figma API responses cached to avoid rate limits
3. **Node ID support** - Fetch specific frames instead of entire files for large designs
4. **Hybrid comparison** - Combines structural and visual analysis for accuracy
5. **OAuth 2.0** - Higher rate limits (vs 2 req/min for personal tokens)

---

## Running the Project

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

### Backend (.env)
```
FIGMA_CLIENT_ID=your_client_id
FIGMA_CLIENT_SECRET=your_client_secret
FIGMA_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback
```

---

*Generated for Figma-Website UI Comparison Tool*
