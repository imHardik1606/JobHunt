import requests
from scanner.base import Job

def fetch_jobs(company_name: str, company_id: str) -> list[Job]:
    """
    Fetches job listings from Ashby public API for a given company.
    """
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Ashby return data in a "jobs" key
        items = data.get("jobs", [])
        
        jobs = []
        for item in items:
            job = Job(
                id=item["id"],
                title=item["title"],
                company=company_name,
                location=item.get("location", "Remote"),
                url=item["jobUrl"],
                description=item.get("descriptionHtml", ""),
                portal="ashby"
            )
            jobs.append(job)
            
        return jobs
        
    except Exception as e:
        print(f"Warning: Failed to fetch jobs from Ashby for {company_name}: {e}")
        return []

if __name__ == "__main__":
    # Test for Linear
    results = fetch_jobs("Linear", "linear")
    print(f"Fetched {len(results)} jobs from Linear.")
    for j in results[:5]:
        print(f"- {j.title} ({j.location}): {j.url}")
