import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys and IDs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# File Paths
CV_PATH = "cv.md"

# Filtering Logic
MIN_SCORE_TO_SHOW = 6.0

# Companies to monitor
COMPANIES = [
    {"name": "Anthropic", "portal": "greenhouse", "id": "anthropic"},
    {"name": "Razorpay", "portal": "greenhouse", "id": "razorpay"},
    {"name": "BrowserStack", "portal": "greenhouse", "id": "browserstack"},
    {"name": "Postman", "portal": "greenhouse", "id": "postman"},
    {"name": "OpenAI", "portal": "greenhouse", "id": "openai"},
    {"name": "Stripe", "portal": "greenhouse", "id": "stripe"},
    {"name": "Airbnb", "portal": "greenhouse", "id": "airbnb"},
    {"name": "Dropbox", "portal": "greenhouse", "id": "dropbox"},
    {"name": "Zepto", "portal": "lever", "id": "zepto"},
    {"name": "Groww", "portal": "lever", "id": "groww"},
    {"name": "Atlassian", "portal": "lever", "id": "atlassian"},
    {"name": "Figma", "portal": "lever", "id": "figma"},
    {"name": "Linear", "portal": "ashby", "id": "linear"},
    {"name": "Vercel", "portal": "ashby", "id": "vercel"},
]

# Keywords for job relevance (Targeting BCA '26 Grad & AI/Backend Profile)
ROLE_KEYWORDS = [
    "intern", "internship", "graduate", "junior", "associate", "new grad", "2026",
    "software engineer", "backend", "python", "developer", "swe",
    "fastapi", "ai engineer", "llm", "rag", "embeddings", "typescript", "golang",
    "api engineer", "full stack", "fullstack", "ml engineer", "founding engineer"
]

# Negative Keywords (Discard senior/unsuitable roles immediately)
NEGATIVE_KEYWORDS = [
    "senior", "sr.", "lead", "staff", "principal", "manager", 
    "director", "head of", "architect", "experienced", 
    "vp", "vice president", "executive", "chief", "founding member",
    "legal", "sales", "marketing", "hr", "recruiter", "accountant"
]

def validate_config() -> bool:
    """
    Validates essential configuration parameters and files.
    """
    # Check Gemini API Key
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY is missing in your .env file.")
        print("💡 Setup: Go to https://aistudio.google.com/ to get a free API key.")
        return False

    # Check CV file existence
    if not os.path.exists(CV_PATH):
        print(f"❌ Error: {CV_PATH} not found.")
        print("💡 Setup: Create a file named 'cv.md' in the project root and paste your CV in markdown format.")
        return False

    # Warn if Google Sheets ID is missing
    if not GOOGLE_SHEETS_ID:
        print("⚠️  Warning: GOOGLE_SHEETS_ID is not set. Tracking to Google Sheets will be disabled.")

    return True
