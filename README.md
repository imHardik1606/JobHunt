# 🎯 JobHunt: AI-Powered Career Pipeline

JobHunt is a personal automation pipeline designed to eliminate the friction of modern job searching. It programmatically scans job portals, scores your fit with deep AI reasoning, and generates hyper-personalized application packages in seconds.

## 🚀 Key Features

- **Department-Aware Scanning**: Target roles in `engineering`, `data`, `product`, `design`, `sales`, or `marketing`.
- **Rich AI Scoring**: Every job gets a **Letter Grade (A-F)**, a numerical score, and a "Top Project" recommendation.
- **Master Application Workflow**: Tailor CV → Generate PDF → Find Outreach Targets → Log to Sheets → Open Browser.
- **Jake's Resume PDF**: Generates professional, single-column LaTeX-style resumes (HTML/CSS → PDF via Playwright).
- **Outreach Research**: Identifies specific hiring managers and writes personalized LinkedIn/Email messages.
- **Sincerely Templates**: Automatically extracts copy-paste ready networking templates for your outreach.
- **Visual Application Tracker**: Logs everything to a professional Google Sheet with color-coded status badges and grades.

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
4. Run `python main.py sheets_setup` for Google Sheets tracking instructions.

### 3. Run the Pipeline
```powershell
# Scan for jobs (default: engineering)
python main.py scan engineering

# View your ranked matches and launch applications
python main.py pipeline

# Or apply directly to a specific job ID
python main.py apply {job_id}
```

## 🕹️ Commands

| Command | Description |
| :--- | :--- |
| `python main.py scan [dept]` | Scans configured companies for roles in the specified department. |
| `python main.py pipeline [score]` | Shows a ranked table of all scored jobs. Default shows 6+. |
| `python main.py apply {id}` | **The Master Workflow**: Runs tailoring, PDF, outreach, and opens browser. |
| `python main.py sheets_setup` | Shows step-by-step instructions for Google Sheets integration. |
| `python main.py status` | Summary of your application pipeline (Pending, Applied, Skipped). |

## 🏗️ Architecture

### Scoring Engine
JobHunt uses **Gemini 1.5 Flash** to perform a "Deep Match" analysis, returning:
- **Grade**: A (Immediate Apply) to F (Not a fit).
- **Top Project**: Which project from your CV will impress *this* hiring manager most.
- **Effort Rating**: How much tailoring is needed (Low/Medium/High).

### Visual Application Tracker
When you run `apply`, JobHunt logs your progress to a Google Sheet with:
- **Color-coded Status**: Applied (Blue), Interviewing (Orange), Offered (Green), Rejected (Red).
- **Grade Heatmap**: Green (A) to Red (F).
- **Score Indicators**: Visual bars based on match confidence.
- **Local Links**: Direct path to your generated tailored resume.

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
