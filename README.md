# 🎯 JobHunt: AI-Powered Career Pipeline

JobHunt is a personal automation pipeline designed to eliminate the friction of modern job searching. It programmatically scans job portals, scores your fit using Gemini AI, and generates tailored, premium resumes in seconds.

## What this does
JobHunt scans high-frequency job portals (Greenhouse, Lever, Ashby) and scores every role against your unique CV using Google Gemini AI. If a role is a match, it generates an advanced tailored resume in PDF format (Jake's Template style) and tracks your application progress in a centralized Google Sheet. **100% free with no monthly subscriptions.**

## Requirements
- **Python 3.10+**
- **Git**
- **Playwright** (for PDF generation)

## Quick Start (5 steps)

### 1. Clone and Setup
```powershell
git clone https://github.com/yourusername/JobHunt.git
cd JobHunt
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
playwright install chromium
```

### 2. Create `cv.md`
Create a file named `cv.md` in the project root. Paste your full CV/Resume in Markdown format. The AI will use this as the "Source of Truth" for all tailoring.

### 3. Add API Key
Copy `.env.example` to `.env` and add your **GEMINI_API_KEY**.
> [!TIP]
> Get a free API key at [aistudio.google.com](https://aistudio.google.com/). It has a generous free tier (15 RPM) which is plenty for personal job hunting.

### 4. Edit `config.py`
Open `config.py` and update the `COMPANIES` list with the organizations you want to monitor. See the "Adding More Companies" section below for details.

### 5. Run Scan and Review
```powershell
# Step A: Scan all portals and score new jobs
python main.py scan

# Step B: Review high-scoring matches and generate resumes
python main.py review
```

## Commands
| Command | What it does | When to use it |
| :--- | :--- | :--- |
| `python main.py scan` | Fetches jobs from all portals in `config.py` and runs AI scoring. | Once or twice a day to find new leads. |
| `python main.py review` | Opens an interactive dashboard to analyze matches and generate PDFs. | After scanning, to decide which roles to apply for. |
| `python main.py status` | Shows a summary of applied vs. pending jobs in your local DB. | To track your overall progress. |
| `python test_pipeline.py` | Verifies your API keys, DB, and PDF tools are working correctly. | During initial setup or troubleshooting. |

## Adding More Companies
To monitor a new company, add a dictionary to the `COMPANIES` list in `config.py`:

```python
{"name": "CompanyName", "portal": "portal_type", "id": "company_id"}
```

**How to find the ID:**
- **Greenhouse**: Look at the public board URL: `boards.greenhouse.io/COMPANY_ID` (e.g., `boards.greenhouse.io/anthropic`)
- **Lever**: Look at the jobs URL: `jobs.lever.co/COMPANY_ID` (e.g., `jobs.lever.co/zepto`)
- **Ashby**: Look at the board URL: `ashbyhq.com/COMPANY_ID` (e.g., `ashbyhq.com/linear`)

## Google Sheets Setup (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a Project and enable **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account**, download the JSON key, rename it to `service_account.json`, and place it in the project root.
4. Create a new Google Sheet and copy its ID from the URL (the part between `/d/` and `/edit`).
5. Add `GOOGLE_SHEETS_ID="your_id_here"` to your `.env` file.
6. **Important**: Share your Google Sheet with the email address of your Service Account.

## Cost
| Component | Provider | Cost |
| :--- | :--- | :--- |
| Job Scraping | Public APIs | ₹0 (Free) |
| AI Scoring/Tailoring | Google Gemini | ₹0 (Free Tier) |
| PDF Generation | Playwright | ₹0 (Open Source) |
| Tracking | Google Sheets | ₹0 (Free) |
| **Total** | | **₹0** |

## Why no auto-apply?
Most modern company portals (Workday, Greenhouse, Lever) use advanced bot-detection and unique CSRF tokens that make automated form submission fragile and prone to blacklisting your IP. More importantly, every application deserves a "sanity check." The real value of JobHunt is in **finding, filtering, and preparing** high-quality applications so you only spend your energy on the top 5% of roles where you actually have a shot.
