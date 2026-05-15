import re
from scanner.greenhouse import fetch_jobs as fetch_greenhouse
from scanner.lever import fetch_jobs as fetch_lever
from scanner.ashby import fetch_jobs as fetch_ashby
from scanner.base import Job
from scanner import ycombinator
from scanner import instahyre
from config import COMPANIES, YC_COMPANIES, get_department_keywords

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

def deduplicate_by_url(jobs: list[Job]) -> list[Job]:
    """
    Removes duplicate jobs based on URL, keeping the first occurrence.
    """
    seen = set()
    unique = []
    for job in jobs:
        if job.url not in seen:
            seen.add(job.url)
            unique.append(job)
    return unique

def scan_all(department: str = "engineering", country: str = None, include_yc: bool = False, include_indian_portals: bool = False) -> list[Job]:
    """
    Orchestrates the scanning of all configured companies across different portals.
    """
    keywords = get_department_keywords(department)
    scan_msg = f"\nScanning for [bold]{department.upper()}[/] roles"
    if country:
        scan_msg += f" in [bold]{country.upper()}[/] (or Remote)"
    print(f"{scan_msg}...")
    
    all_relevant_jobs = []
    
    # Prepare company list
    target_companies = COMPANIES.copy()
    if include_yc:
        target_companies.extend(YC_COMPANIES)
        # Deduplicate target_companies by ID to avoid scanning same company twice if it's in both lists
        seen_ids = set()
        final_targets = []
        for c in target_companies:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                final_targets.append(c)
        target_companies = final_targets

    for company in target_companies:
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
                # Filter by location if country is provided
                if country:
                    loc = job.location.lower()
                    target = country.lower()
                    if target not in loc and "remote" not in loc and "anywhere" not in loc:
                        continue

                job.department = department
                all_relevant_jobs.append(job)
                relevant_count += 1
        
        print(f"Found {relevant_count} relevant jobs at {name}")
        
    # Optional: Scan YC Work at a Startup job board
    if include_yc:
        print("\nScanning Work at a Startup (YC job board)...")
        try:
            yc_jobs_dicts = ycombinator.fetch_jobs(job_type="both", remote_only=False)
            yc_relevant_count = 0
            for jd in yc_jobs_dicts:
                # Convert dict to Job object
                job = Job(
                    id=jd["id"],
                    title=jd["title"],
                    company=jd["company"],
                    location=jd["location"],
                    url=jd["url"],
                    description=jd["description"],
                    portal=jd["portal"]
                )
                
                # Clean and filter
                job.description = clean_html(job.description)
                if is_relevant(job, keywords):
                    if country:
                        loc = job.location.lower()
                        target = country.lower()
                        if target not in loc and "remote" not in loc and "anywhere" not in loc:
                            continue
                    
                    job.department = department
                    all_relevant_jobs.append(job)
                    yc_relevant_count += 1
            print(f"  → {yc_relevant_count} relevant YC listings found")
        except Exception as e:
            print(f"❌ Error: Failed to fetch from YC job board: {e}")

    # Optional: Scan Indian Portals (Instahyre)
    if include_indian_portals:
        print("\nScanning Indian portals (Instahyre)...")
        try:
            # We map department keywords to search terms for Instahyre
            instahyre_jobs = instahyre.fetch_jobs(roles=keywords[:3], location=country if country else "India")
            insta_relevant_count = 0
            for jd in instahyre_jobs:
                job = Job(
                    id=jd["id"],
                    title=jd["title"],
                    company=jd["company"],
                    location=jd["location"],
                    url=jd["url"],
                    description=jd["description"],
                    portal=jd["portal"]
                )
                job.description = clean_html(job.description)
                if is_relevant(job, keywords):
                    # For Instahyre we already filtered by location in the fetch_jobs call
                    # but we keep the logic for consistency
                    if country:
                        loc = job.location.lower()
                        target = country.lower()
                        if target not in loc and "remote" not in loc and "anywhere" not in loc:
                            continue
                            
                    job.department = department
                    all_relevant_jobs.append(job)
                    insta_relevant_count += 1
            print(f"  → {insta_relevant_count} relevant Instahyre listings found")
        except Exception as e:
            print(f"❌ Error: Failed to fetch from Instahyre: {e}")

    return deduplicate_by_url(all_relevant_jobs)
