import requests
from scanner.base import Job

def fetch_jobs(company_name: str, company_id: str) -> list[Job]:
    """
    Fetches job listings from Lever public API for a given company.
    """
    url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for item in data:
            # Build description from 'lists'
            desc_parts = []
            for section in item.get("lists", []):
                header = section.get("text", "")
                content = section.get("content", "").replace("<li>", "").replace("</li>", " ")
                desc_parts.append(f"{header} {content}")
            
            description = " ".join(desc_parts).strip()
            
            job = Job(
                id=item["id"],
                title=item["text"],
                company=company_name,
                location=item.get("categories", {}).get("location", "Remote"),
                url=item["hostedUrl"],
                description=description,
                portal="lever"
            )
            jobs.append(job)
        return jobs
        
    except Exception as e:
        print(f"Warning: Failed to fetch jobs from Lever for {company_name}: {e}")
        return []

if __name__ == "__main__":
    # Test for Palantir (Netflix uses Workday now)
    results = fetch_jobs("Palantir", "palantir")
    print(f"Fetched {len(results)} jobs from Palantir.")
    for j in results[:3]:
        print(f"- {j.title} ({j.location})")
