# 🎯 JobHunt: AI-Powered Career Pipeline

JobHunt is a personal automation pipeline designed to eliminate the friction of modern job searching. It programmatically scans job portals, scores your fit with deep AI reasoning, and generates hyper-personalized application packages in seconds.

## 🚀 Key Features

- **Department-Aware Scanning**: Target roles in `engineering`, `data`, `product`, `design`, `sales`, or `marketing`.
- **Rich AI Scoring**: Every job gets a **Letter Grade (A-F)**, a numerical score, and a "Top Project" recommendation.
- **Humanized Tailoring**: AI prompt engineering that eliminates "robotic" buzzwords and focuses on concrete outcomes.
- **Jake's Resume PDF**: Generates professional, single-column LaTeX-style resumes (HTML/CSS → PDF via Playwright).
- **Outreach Research**: Identifies specific hiring managers and writes personalized LinkedIn/Email messages.
- **Sincerely Templates**: Automatically extracts copy-paste ready networking templates for your outreach.
- **Centralized Tracking**: Local SQLite database for persistence + optional Google Sheets syncing.

## 📋 Requirements
- **Python 3.10+**
- **Git**
- **Playwright** (for PDF generation)
- **Gemini API Key** (Free tier available)

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
2. Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`.
3. Update `config.py` with the companies you want to monitor.

### 3. Run the Pipeline
```powershell
# Scan for jobs (default: engineering)
python main.py scan engineering

# View your ranked matches
python main.py pipeline

# Start the full application workflow for a specific job
python main.py apply {job_id}
```

## 🕹️ Commands

| Command | Description |
| :--- | :--- |
| `python main.py scan [dept]` | Scans all configured companies for roles in the specified department. |
| `python main.py pipeline [score]` | Shows a ranked table of all scored jobs. Default shows 6+. |
| `python main.py apply {id}` | **The Master Workflow**: Tailors CV → Generates PDF → Finds Outreach Targets. |
| `python main.py review [dept]` | Interactive dashboard to deep-dive into job descriptions. |
| `python main.py status` | Summary of your application pipeline (Pending, Applied, Skipped). |

## 🏗️ Architecture

### Scoring Engine
JobHunt doesn't just look for keywords. It uses **Gemini 1.5 Flash** to perform a "Deep Match" analysis, returning:
- **Grade**: A (Immediate Apply) to F (Not a fit).
- **Match Reasons**: 3 specific technical strengths.
- **Gaps**: Skills or experience you're missing.
- **Top Project**: Which project from your CV will impress *this* hiring manager most.
- **Effort Rating**: How much tailoring is needed (Low/Medium/High).

### Application Package
When you run `apply`, JobHunt generates an `output/` folder containing:
1. `Company_Role_tailored.md`: Your AI-optimized resume source.
2. `Company_Role_Jake.pdf`: A premium, ready-to-send PDF.
3. `sincerely_Company_Role.md`: Personalized outreach messages for 4-5 specific people at the company.

## 🤝 Adding Companies
To monitor a new company, add it to `COMPANIES` in `config.py`:
```python
{"name": "Anthropic", "portal": "greenhouse", "id": "anthropic"}
```
Support portals: `greenhouse`, `lever`, `ashby`.

## 💰 Cost
- **Job Scraping**: ₹0 (Public APIs)
- **AI Engine**: ₹0 (Gemini Free Tier)
- **PDF Generation**: ₹0 (Playwright)
- **Total**: **₹0**

> [!IMPORTANT]
> Find each outreach target manually using the search strings generated in the report. Replace `[FIRSTNAME]` before sending. Quality > quantity.
