import re
from scanner.greenhouse import fetch_jobs as fetch_greenhouse
from scanner.lever import fetch_jobs as fetch_lever
from scanner.ashby import fetch_jobs as fetch_ashby
from scanner.base import Job
from config import COMPANIES, get_department_keywords

PORTAL_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby
}

def clean_html(text: str) -> str:
    """
    Strips HTML tags and decodes common entities to leave clean text.
    """
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    
    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    
    # Collapse multiple spaces and strip
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_relevant(job: Job, keywords: list[str]) -> bool:
    """
    Checks if a job is relevant based on keywords.
    Case-insensitive match against title and description.
    """
    search_text = (job.title + " " + job.description).lower()
    return any(keyword.lower() in search_text for keyword in keywords)

def scan_all(department: str = "engineering") -> list[Job]:
    """
    Orchestrates the scanning of all configured companies across different portals.
    """
    keywords = get_department_keywords(department)
    print(f"\nScanning for [bold]{department.upper()}[/] roles...")
    
    all_relevant_jobs = []
    
    for company in COMPANIES:
        name = company["name"]
        portal = company["portal"]
        company_id = company["id"]
        
        fetcher = PORTAL_FETCHERS.get(portal)
        if not fetcher:
            print(f"⚠️  Skip: Unknown portal '{portal}' for {name}")
            continue
            
        print(f"Scanning {name} ({portal})...")
        try:
            jobs = fetcher(name, company_id)
            if not jobs:
                print(f"⚠️  Warning: {name} ({portal}) returned 0 jobs.")
                continue
        except Exception as e:
            print(f"❌ Error: Failed to fetch from {name} ({portal}): {e}")
            continue
        
        relevant_count = 0
        for job in jobs:
            # Clean description for relevance check and for later AI use
            job.description = clean_html(job.description)
            
            if is_relevant(job, keywords):
                job.department = department
                all_relevant_jobs.append(job)
                relevant_count += 1
        
        print(f"Found {relevant_count} relevant jobs at {name}")
        
    return all_relevant_jobs
