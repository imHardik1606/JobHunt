# 🎯 JobHunt: AI-Powered Career Pipeline

JobHunt is a personal automation pipeline designed to eliminate the friction of modern job searching. It programmatically scans job portals, scores your fit with deep AI reasoning, and generates hyper-personalized application packages in seconds.

## 🚀 Key Features

- **Parallel Multi-Key Scoring**: High-performance scoring using a pool of multiple API keys (Gemini, Groq, OpenRouter) with automatic rotation and rate-limit handling.
- **YC Startup Discovery**: Specialized scraper for the **Work at a Startup** (YCombinator) job board and a curated list of top YC startups.
- **Indian Portal Support**: Automated scraping for Indian platforms like **Instahyre** with role and location-based targeting.
- **Department-Aware Scanning**: Target roles in `engineering`, `data`, `product`, `design`, `sales`, or `marketing`.
- **Rich AI Scoring**: Every job gets a **Letter Grade (A-F)**, a numerical score, a "Top Project" recommendation, and a "Match Verdict".
- **Master Application Workflow**: Tailor CV -> Generate PDF -> Find Outreach Targets -> Log to Sheets -> Open Browser.
- **Jake's Resume PDF**: Generates professional, single-column LaTeX-style resumes (HTML/CSS -> PDF via Playwright).
- **Outreach Research**: Identifies specific hiring managers and writes personalized LinkedIn/Email messages.
- **Visual Application Tracker**: Logs everything to a professional Google Sheet with color-coded status badges and grades.

## 📋 Requirements
- **Python 3.10+**
- **Git**
- **Playwright** (for PDF generation and web scraping)
- **API Keys**: Gemini (primary), Groq, or OpenRouter (optional for parallel speedup)

## 🛠️ Quick Start

### 1. Setup Environment
```powershell
git clone https://github.com/imHardik1606/JobHunt.git
cd JobHunt
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure
1. Create `cv.md` in the root and paste your full CV in Markdown.
2. Copy `.env.example` to `.env` and add your keys.
   - **Pro Tip**: Add multiple keys like `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GROQ_API_KEY_1` to enable high-speed parallel scoring.
3. Update `config.py` with the companies you want to monitor.
4. Run `python main.py sheets_setup` for Google Sheets tracking instructions.

### 3. Run the Pipeline
```powershell
# Scan for Engineering roles in India, including YC companies
python main.py scan engineering india yc

# View your ranked matches and launch applications
python main.py pipeline

# Or apply directly to a specific job ID
python main.py apply {job_id}
```

## 🕹️ Commands

| Command | Description |
| :--- | :--- |
| `python main.py scan [dept] [flags]` | Scans jobs with optional flags: `india`, `remote`, `yc`. |
| `python main.py pipeline [score]` | Shows a ranked table of all scored jobs. Default shows 6+. |
| `python main.py apply {id}` | **The Master Workflow**: Runs tailoring, PDF, outreach, and logs results. |
| `python main.py sheets_setup` | Shows step-by-step instructions for Google Sheets integration. |
| `python main.py status` | Summary of your application pipeline statistics. |

### Flag Examples:
- `python main.py scan engineering yc` -> Only YC companies & YC job board.
- `python main.py scan data remote` -> Data roles, remote only.
- `python main.py scan engineering india yc` -> Engineering roles in India + YC startups.

## 🏗️ Architecture

### High-Speed Scoring Engine
JobHunt uses a **KeyPool** architecture to distribute scoring tasks across multiple AI models:
- **Parallel Workers**: Automatically calculates the optimal number of workers based on your available API keys.
- **Failover Logic**: If Gemini hits a rate limit, the system automatically rotates to Groq or another Gemini key.
- **Model Support**: `gemini-1.5-flash`, `llama3-8b` (via Groq), and `openrouter/free` meta-models.

### Discovery Pipeline
The discovery engine combines direct portal API calls with browser-based scraping:
- **Direct**: Greenhouse, Lever, and Ashby APIs for 100+ top companies.
- **Scraped**: YCombinator (Work at a Startup) and Instahyre via Playwright.
- **Deduplication**: Automatic global deduplication by URL across all sources.

## 🤝 Customization
To monitor a new company, add it to `COMPANIES` in `config.py`:
```python
{"name": "Anthropic", "portal": "greenhouse", "id": "anthropic"}
```
Support portals: `greenhouse`, `lever`, `ashby`.

## 💰 Cost
- **Job Discovery**: ₹0 (Public APIs & Playwright)
- **AI Scoring**: ₹0 (Gemini/Groq/OpenRouter Free Tiers)
- **Resume PDF**: ₹0 (Playwright)
- **Total**: **₹0**

> [!IMPORTANT]
> The parallel scoring engine is extremely fast. Ensure you have enough API keys in `.env` to sustain high worker counts.
