# eCourts Order Date Search Website & Bridge

A standalone, modern web application that allows citizens and advocates to search for Indian court orders using **strictly** the **Order Date** search functionality from the official Indian eCourts portal (`services.ecourts.gov.in`).

> **Notice:** This is an independent open-access interface and is **not** affiliated with or endorsed by the official eCourts government system. All official court orders remain the authentic public records of the Indian Judiciary.

---

## 1. Key Features

- **Strict Functional Scope:**
  - Implements only the **Order Date** search tab criteria.
  - Three location text inputs: `State`, `District`, and `Court Complex` (users type manually; no dropdowns or autocompletes on the frontend).
  - Exact Order Date fields matching the official portal: `*From Date` (DD-MM-YYYY), `*To Date` (DD-MM-YYYY), and Order Type radios (`Interim Orders`, `Final Orders`, `Both`).
  - Manual in-line CAPTCHA challenge presentation and submission.
  - Interactive Help/How-To collapsible guide.
  - Direct links to **Open Official Order** documents (open securely in new browser tabs).
- **Intelligent Sequential Location Mapping:**
  - Backend maps manually typed State, District, and Court Complex names to the official nested dropdown options on the live site.
  - Handles whitespace trimming, case-insensitivity, and exact matching.
  - Detects and cleanly reports `UNMATCHED_STATE`, `UNMATCHED_DISTRICT`, `UNMATCHED_COURT_COMPLEX`, and ambiguous matches.
- **Zero Persistent Storage:**
  - **No database** (no SQLite, PostgreSQL, MongoDB, Redis, or Celery).
  - Strictly ephemeral, in-memory search session tracking with automatic expiration (5 minutes TTL).
  - No storage of search history, search criteria, results, PDFs, or browser profiles.
- **Dual Live & Resilient Demonstration Mode:**
  - Full Playwright Chromium browser automation for live interactions.
  - Fallback/mock mode (`ECOURTS_MOCK_MODE=true` or automatic fallback) when external government portals are unreachable or geo-restricted.

---

## 2. Technology Stack

- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript, Fetch API.
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic v2.
- **Automation / Scraping:** Playwright (Async Python API), BeautifulSoup4, HTTPX, Pillow (PIL).
- **Testing:** Pytest, Pytest-AsyncIO, HTTPX AsyncClient.

---

## 3. Project Structure

```text
ecourts-order-date-search/
├── frontend/
│   ├── index.html          # Single-page responsive interface
│   ├── css/
│   │   └── style.css       # Custom styles & design tokens
│   └── js/
│       ├── app.js          # App bootstrap & datepicker helpers
│       ├── search.js       # Search form submission & state machine
│       └── results.js      # Results rendering & CSV export
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Configuration & environment loader
│   │   ├── schemas.py      # Pydantic models & validation rules
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── search.py   # REST API endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── ecourts_scraper.py   # Playwright scraper & location mapper
│   │       └── session_manager.py   # In-memory session manager
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_schemas.py          # Request validation unit tests
│   │   ├── test_session_manager.py  # Session manager unit tests
│   │   ├── test_scraper_mock.py     # Location matching & HTML parser tests
│   │   └── test_api.py              # FastAPI endpoint integration tests
│   └── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Windows Local Setup Instructions

### Prerequisites
- Windows 10/11
- Python 3.12 or higher installed (`python --version`)

### Step 1: Open PowerShell or Command Prompt
Navigate to the project root directory:
```powershell
cd c:\Users\HEMANTH\OneDrive\Desktop\DOPAMS-Court
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If using `uv`: `uv venv .venv` followed by `.\.venv\Scripts\Activate.ps1`)*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Install Playwright Chromium Browser
```powershell
playwright install chromium
```

### Step 5: (Optional) Configure Environment
Copy `.env.example` to `.env`:
```powershell
cp ecourts-order-date-search\.env.example ecourts-order-date-search\.env
```
To run in offline simulation / mock mode (recommended for local testing or when outside India / geo-blocked):
Set `ECOURTS_MOCK_MODE=true` in `.env`.

### Step 6: Start the Server
Run the FastAPI development server:
```powershell
cd ecourts-order-date-search\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Or run `python run.py` directly from the workspace root.

### Step 7: Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 5. Running the Automated Tests

Execute the unit and integration tests using pytest:

```powershell
cd c:\Users\HEMANTH\OneDrive\Desktop\DOPAMS-Court\ecourts-order-date-search\backend
pytest -v
```

All tests run completely offline and use mocked fixtures and responses.

---

## 6. How To Use The Website

1. **Enter Location Text Manually:**
   - **State:** e.g., `Delhi`
   - **District:** e.g., `New Delhi`
   - **Court Complex:** e.g., `Patiala House Courts`
2. **Specify Order Date Range:**
   - **From Date:** `01-01-2024` (or pick using the calendar button)
   - **To Date:** `10-01-2024`
   - **Order Type:** Select `Interim Orders` (default), `Final Orders`, or `Both`.
3. **Click "Go":**
   - The backend validates all inputs and initializes the browser session.
   - If manual CAPTCHA verification is required, the challenge image will be presented on screen.
   - Enter the characters in the `*Enter Captcha` field and click `Submit Captcha` (or hit Enter).
4. **View & Open Orders:**
   - Matching orders appear in the responsive table.
   - Click `Open Official Order` to view the authentic eCourts PDF directly.
5. **Reset:**
   - Clicking `Reset` immediately clears the form, cancels active scraping tasks, and releases all browser memory.

---

## 7. Known Limitations & Technical Notes

1. **Official eCourts Geo-Fencing & IP Rate Limiting:**
   - The official Indian eCourts portal frequently enforces geographic IP restrictions (blocking requests from cloud IPs or outside India) and strict Cloudflare / NIC WAF rules.
   - To guarantee smooth operation and verifiable demonstration during development and testing, an automatic resilient simulation mode (`ECOURTS_MOCK_MODE`) is built-in.
2. **No Persistent History by Design:**
   - In accordance with the prompt's strict requirements, no database or cache is utilized. Sessions expire after 5 minutes of inactivity.
3. **CAPTCHA Policy:**
   - Automated bypass or third-party solving services are strictly prohibited. The system presents the CAPTCHA to the user for manual entry and forwards the solution to the browser session.
