import requests
from scanner.base import Job

def fetch_jobs(company_name: str, company_id: str) -> list[Job]:
    """
    Fetches job listings from Greenhouse public API for a given company.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs?content=true"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for item in data.get("jobs", []):
            job = Job(
                id=str(item["id"]),
                title=item["title"],
                company=company_name,
                location=item.get("location", {}).get("name", "Remote"),
                url=item["absolute_url"],
                description=item.get("content", ""),
                portal="greenhouse"
            )
            jobs.append(job)
        return jobs
        
    except Exception as e:
        print(f"Warning: Failed to fetch jobs from Greenhouse for {company_name}: {e}")
        return []

if __name__ == "__main__":
    # Test for Anthropic
    results = fetch_jobs("Anthropic", "anthropic")
    print(f"Fetched {len(results)} jobs from Anthropic.")
    for j in results[:3]:
        print(f"- {j.title} ({j.location})")
