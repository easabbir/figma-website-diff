# Figma-Website UI Comparison Tool - Codebase Analysis

## 1. Project Structure

```
figma-website-diff/
├── backend/                    # FastAPI Python Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py    # Main API routes (comparison, history, OAuth)
│   │   │   ├── auth_endpoints.py # Authentication routes
│   │   │   └── websocket.py    # WebSocket for real-time progress
│   │   ├── models/
│   │   │   ├── database.py     # SQLite database operations
│   │   │   ├── schemas.py      # Pydantic models/DTOs
│   │   │   └── user.py         # User model
│   │   ├── services/
│   │   │   ├── auth.py         # JWT authentication
│   │   │   ├── comparator.py   # UI comparison logic
│   │   │   ├── email_service.py # OTP email sending
│   │   │   ├── figma_extractor.py # Figma API integration
│   │   │   ├── figma_oauth.py  # Figma OAuth 2.0
│   │   │   ├── pdf_generator.py # PDF report generation
│   │   │   ├── report_generator.py # HTML report generation
│   │   │   └── web_analyzer.py # Playwright website capture
│   │   ├── utils/
│   │   ├── config.py           # App configuration
│   │   └── main.py             # FastAPI app entry point
│   ├── data/                   # SQLite DB & token storage
│   ├── outputs/                # Generated reports
│   └── requirements.txt
│
├── frontend/                   # React + TypeScript Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthPage.tsx    # Login/Signup UI
│   │   │   ├── ComparisonForm.tsx # Main comparison form
│   │   │   ├── ReportDisplay.tsx # Report viewer with slider
│   │   │   ├── HistoryView.tsx # Comparison history
│   │   │   ├── ProfilePage.tsx # User profile settings
│   │   │   ├── FigmaOAuth.tsx  # Figma connection UI
│   │   │   ├── Header.tsx      # App header
│   │   │   └── DiffViewer.tsx  # Difference visualization
│   │   ├── context/
│   │   │   └── AuthContext.tsx # Authentication state
│   │   ├── App.tsx             # Main app component
│   │   └── main.tsx            # React entry point
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml          # Docker orchestration
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ AuthPage │  │Comparison│  │  Report  │  │   HistoryView    │ │
│  │          │  │   Form   │  │ Display  │  │                  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │             │             │                  │          │
│       └─────────────┴─────────────┴──────────────────┘          │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    │   AuthContext     │                        │
│                    │ (Global State)    │                        │
│                    └─────────┬─────────┘                        │
└──────────────────────────────┼──────────────────────────────────┘
                               │ HTTP/WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      API Layer                           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │   │
│  │  │  /compare  │  │  /history  │  │  /auth/*           │ │   │
│  │  │  /report   │  │  /oauth/*  │  │  /profile          │ │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘ │   │
│  └────────┼───────────────┼───────────────────┼────────────┘   │
│           │               │                   │                 │
│  ┌────────┴───────────────┴───────────────────┴────────────┐   │
│  │                    Service Layer                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │FigmaExtractor│  │ WebAnalyzer  │  │  UIComparator  │ │   │
│  │  │              │  │ (Playwright) │  │                │ │   │
│  │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │   │
│  │         │                 │                  │          │   │
│  │  ┌──────┴─────────────────┴──────────────────┴────────┐ │   │
│  │  │              ReportGenerator / PDFGenerator        │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌───────────────────────────┴───────────────────────────────┐ │
│  │                      Data Layer                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │ │
│  │  │   SQLite    │  │Token Storage│  │   File System     │  │ │
│  │  │ (users,     │  │ (OAuth)     │  │ (screenshots,     │  │ │
│  │  │ comparisons)│  │             │  │  reports)         │  │ │
│  │  └─────────────┘  └─────────────┘  └───────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Figma    │    │ Website  │    │  Email   │
        │ API      │    │ (Target) │    │  (SMTP)  │
        └──────────┘    └──────────┘    └──────────┘
```

---

## 3. Logic Flow

### 3.1 Authentication Flow
```
User → AuthPage → POST /auth/signup/request-otp → Email OTP
                → POST /auth/signup/verify-otp → JWT Token → AuthContext
                → POST /auth/login → JWT Token → AuthContext
```

### 3.2 Comparison Flow
```
1. User fills ComparisonForm (Figma URL + Website URL)
2. POST /compare → Creates job_id, starts background task
3. Background task:
   a. FigmaExtractor → Fetches design from Figma API
   b. WebAnalyzer → Captures website screenshot (Playwright)
   c. UIComparator → Compares images/structure
   d. ReportGenerator → Creates HTML/JSON report
4. WebSocket sends progress updates
5. ReportDisplay shows results with slider comparison
```

### 3.3 Figma OAuth Flow
```
User → FigmaOAuth component → GET /oauth/authorize → Figma Login
     → Figma redirects to /oauth/callback → Token stored
     → User can now access their Figma files
```

---

## 4. Key Module Interactions

| Module | Depends On | Provides |
|--------|------------|----------|
| `endpoints.py` | All services, database | REST API |
| `FigmaExtractor` | Figma API, OAuth tokens | Design data, screenshots |
| `WebAnalyzer` | Playwright | Website screenshots, DOM |
| `UIComparator` | PIL, OpenCV | Difference detection |
| `ReportGenerator` | Jinja2 | HTML reports |
| `PDFGenerator` | ReportLab | PDF reports |
| `database.py` | SQLite | User/comparison persistence |
| `AuthContext.tsx` | axios | Frontend auth state |

---

## 5. Anti-Patterns & Potential Bugs

### 🔴 Critical Issues

1. ~~**In-Memory Job Storage** (`endpoints.py:43-44`)~~ ✅ **FIXED**
   - Now uses Redis with automatic fallback to in-memory storage
   - See `job_storage.py` for implementation

2. ~~**Hardcoded Frontend URL** (`endpoints.py:843`)~~ ✅ **FIXED**
   - Now uses `settings.FRONTEND_URL` from environment variable
   - Configure via `FRONTEND_URL` in `.env`

3. **Token Storage in JSON File** (`figma_oauth.py:24`)
   ```python
   TOKEN_STORAGE_FILE = Path(...) / "oauth_tokens.json"
   ```
   - **Problem**: Not secure, not scalable
   - **Fix**: Store encrypted tokens in database

### 🟡 Warnings

4. **No Rate Limiting**
   - API endpoints have no rate limiting
   - Vulnerable to abuse/DoS

5. **Broad Exception Handling** (multiple files)
   ```python
   except Exception as e:
       pass  # Column already exists
   ```
   - Swallows errors silently

6. **Missing Input Validation**
   - URLs not validated for SSRF attacks
   - File uploads not properly sanitized

7. **Synchronous Figma API Calls**
   - `FigmaExtractor` uses `requests` (blocking)
   - Should use `httpx` async

8. **No Database Migrations**
   - Schema changes done via `ALTER TABLE` with try/except
   - Should use Alembic

### 🟢 Minor Issues

9. **Inconsistent Error Messages**
   - Some return detailed errors, others generic

10. **No Request ID Tracking**
    - Hard to trace issues across services

11. **Missing Type Hints** (some functions)

---

## 6. Refactoring Recommendations

### High Priority

1. **Add Redis for Job State**
   ```python
   # Instead of in-memory dict
   from redis import Redis
   redis_client = Redis(host='localhost', port=6379)
   ```

2. **Environment-Based Configuration**
   ```python
   # config.py
   FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
   ```

3. **Database Token Storage**
   ```python
   # Add to database.py
   CREATE TABLE oauth_tokens (
       user_id TEXT PRIMARY KEY,
       access_token TEXT ENCRYPTED,
       refresh_token TEXT ENCRYPTED,
       expires_at TIMESTAMP
   )
   ```

4. **Add Rate Limiting**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @router.post("/compare")
   @limiter.limit("10/minute")
   async def compare(...):
   ```

### Medium Priority

5. **Async HTTP Client**
   ```python
   # Replace requests with httpx
   import httpx
   async with httpx.AsyncClient() as client:
       response = await client.get(figma_url)
   ```

6. **Database Migrations with Alembic**
   ```bash
   alembic init migrations
   alembic revision --autogenerate -m "Add comparison_number"
   alembic upgrade head
   ```

7. **Structured Logging**
   ```python
   import structlog
   logger = structlog.get_logger()
   logger.info("comparison_started", job_id=job_id, user_id=user_id)
   ```

### Low Priority

8. **API Versioning Strategy**
   - Current: `/api/v1/`
   - Add deprecation headers for future versions

9. **OpenAPI Documentation**
   - Add more detailed descriptions
   - Include example requests/responses

10. **Unit Test Coverage**
    - Add pytest tests for services
    - Add React Testing Library tests

---

## 7. Recommended Documentation & Diagrams

### Create These Documents:

1. **API_REFERENCE.md**
   - All endpoints with request/response examples
   - Authentication requirements
   - Error codes

2. **DEPLOYMENT.md**
   - Production setup guide
   - Environment variables
   - Docker/Kubernetes configs

3. **CONTRIBUTING.md**
   - Code style guide
   - PR process
   - Testing requirements

### Create These Diagrams:

1. **Sequence Diagram** - Comparison flow
2. **ERD** - Database schema
3. **Component Diagram** - Frontend architecture
4. **Deployment Diagram** - Infrastructure

---

## 8. Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| JWT Token Expiry | ✅ | 30 min default |
| Password Hashing | ✅ | bcrypt |
| CORS Configuration | ⚠️ | Too permissive in dev |
| SQL Injection | ✅ | Parameterized queries |
| XSS Protection | ✅ | React escapes by default |
| CSRF Protection | ⚠️ | OAuth state validation weak |
| Rate Limiting | ❌ | Not implemented |
| Input Validation | ⚠️ | Partial |
| Secrets Management | ⚠️ | .env file (use vault in prod) |
| HTTPS | ❌ | Not enforced |

---

## 9. Performance Considerations

1. **Screenshot Capture** - Most expensive operation (~5-15s)
   - Consider caching recent screenshots
   - Add timeout limits

2. **Database Queries** - Currently efficient
   - Add indexes on `user_id`, `created_at`

3. **Image Processing** - Memory intensive
   - Consider streaming for large images
   - Add max file size limits

4. **WebSocket Connections** - No connection pooling
   - Add connection limits per user

---

## 10. Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Database | SQLite (dev), PostgreSQL (prod recommended) |
| Browser Automation | Playwright |
| Image Processing | Pillow, OpenCV |
| PDF Generation | ReportLab |
| Authentication | JWT (PyJWT) |
| Email | SMTP (Gmail) |
| Containerization | Docker, Docker Compose |

---

*Generated: December 2024*
