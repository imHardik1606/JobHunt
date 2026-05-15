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

# YC-specific companies (optionally merged via --yc flag)
YC_COMPANIES = [
    # Batch S24 / W24 — recent
    {"name": "Firecrawl",       "portal": "greenhouse", "id": "firecrawl"},
    {"name": "Browserbase",     "portal": "greenhouse", "id": "browserbase"},
    {"name": "Groq",            "portal": "greenhouse", "id": "groq"},
    {"name": "Together AI",     "portal": "greenhouse", "id": "togetherai"},
    {"name": "Anyscale",        "portal": "greenhouse", "id": "anyscale"},
    {"name": "Modal",           "portal": "lever",      "id": "modal-labs"},
    {"name": "Replicate",       "portal": "lever",      "id": "replicate"},
    {"name": "Weights & Biases","portal": "lever",      "id": "wandb"},

    # Established YC alumni — actively hiring
    {"name": "Stripe",          "portal": "greenhouse", "id": "stripe"},
    {"name": "Airbnb",          "portal": "greenhouse", "id": "airbnb"},
    {"name": "Dropbox",         "portal": "greenhouse", "id": "dropbox"},
    {"name": "Gusto",           "portal": "greenhouse", "id": "gusto"},
    {"name": "Rippling",        "portal": "greenhouse", "id": "rippling"},
    {"name": "Brex",            "portal": "greenhouse", "id": "brex"},
    {"name": "Retool",          "portal": "greenhouse", "id": "retool"},
    {"name": "Deel",            "portal": "greenhouse", "id": "deel"},
    {"name": "Clerk",           "portal": "greenhouse", "id": "clerk"},
    {"name": "Vercel",          "portal": "lever",      "id": "vercel"},
    {"name": "Supabase",        "portal": "ashby",      "id": "supabase"},
    {"name": "Linear",          "portal": "ashby",      "id": "linear"},
    {"name": "Loom",            "portal": "greenhouse", "id": "loom"},
    {"name": "Webflow",         "portal": "greenhouse", "id": "webflow"},
    {"name": "Amplitude",       "portal": "greenhouse", "id": "amplitude"},
    {"name": "Segment",         "portal": "greenhouse", "id": "segment"},
    {"name": "Mixpanel",        "portal": "greenhouse", "id": "mixpanel"},
    {"name": "PostHog",         "portal": "ashby",      "id": "posthog"},
    {"name": "Descript",        "portal": "greenhouse", "id": "descript"},
    {"name": "Scale AI",        "portal": "greenhouse", "id": "scaleai"},
    {"name": "Cohere",          "portal": "greenhouse", "id": "cohere"},
    {"name": "Perplexity",      "portal": "ashby",      "id": "perplexityai"},
    {"name": "Harvey",          "portal": "ashby",      "id": "harvey"},
    {"name": "Cursor",          "portal": "ashby",      "id": "anysphere"},
    {"name": "Glean",           "portal": "greenhouse", "id": "glean"},
    {"name": "Coda",            "portal": "greenhouse", "id": "coda"},
    {"name": "Notion",          "portal": "greenhouse", "id": "notion"},
    {"name": "Figma",           "portal": "greenhouse", "id": "figma"},

    # YC India-connected or remote-friendly
    {"name": "Razorpay",        "portal": "greenhouse", "id": "razorpay"},
    {"name": "Postman",         "portal": "greenhouse", "id": "postman"},
    {"name": "BrowserStack",    "portal": "greenhouse", "id": "browserstack"},
    {"name": "Hasura",          "portal": "lever",      "id": "hasura"},
    {"name": "Setu",            "portal": "lever",      "id": "setu"},
]

# Department-specific keywords for job relevance
DEPARTMENTS = {
    "engineering": [
        "software engineer", "backend", "frontend", "full stack", "fullstack",
        "ml engineer", "data engineer", "devops", "platform", "infrastructure",
        "sre", "mobile", "ios", "android", "api", "python", "node", "golang"
    ],
    "data": [
        "data scientist", "data analyst", "machine learning", "ml", "ai",
        "research scientist", "analytics", "data engineer", "nlp"
    ],
    "product": [
        "product manager", "pm", "product analyst", "product designer"
    ],
    "design": [
        "designer", "ux", "ui", "product design", "figma"
    ],
    "sales": [
        "sales", "account executive", "business development", "bdm", "bdr", "sdr"
    ],
    "marketing": [
        "marketing", "growth", "content", "seo", "performance marketing"
    ],
}

DEFAULT_DEPARTMENT = "engineering"

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

def get_department_keywords(department: str) -> list[str]:
    dept = department.lower().strip()
    if dept not in DEPARTMENTS:
        available = ", ".join(DEPARTMENTS.keys())
        raise ValueError(f"Unknown department '{dept}'. Available: {available}")
    return DEPARTMENTS[dept]
