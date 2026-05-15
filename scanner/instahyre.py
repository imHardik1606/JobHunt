import asyncio
import hashlib
import time
from playwright.async_api import async_playwright
from scanner.base import Job

async def _scrape_instahyre(role: str, location: str) -> list[dict]:
    """
    Scrapes Instahyre job listings for a given role and location using Playwright.
    """
    url = f"https://www.instahyre.com/search-jobs/?keyword={role}&location={location}"
    print(f"Scraping Instahyre for '{role}' in '{location}'...")
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # Use robust selectors found by subagent
                try:
                    await page.wait_for_selector("a#employer-profile-opportunity, .job-card", timeout=15000)
                except:
                    print(f"Wait for selector timed out for '{role}', but proceeding.")
            except Exception as e:
                print(f"Error navigating to '{role}': {e}")
                return []

            # Find all job cards (new selector)
            job_elements = await page.query_selector_all("a#employer-profile-opportunity, .job-card")
            jobs = []

            for element in job_elements:
                try:
                    # Extract title and company (often combined in Instahyre's new layout)
                    header_elem = await element.query_selector("div:nth-child(2) > div:nth-child(1) > div")
                    header_text = await header_elem.inner_text() if header_elem else ""
                    
                    if " - " in header_text:
                        company, title = [part.strip() for part in header_text.split(" - ", 1)]
                    else:
                        title = header_text or "N/A"
                        company = "N/A"

                    # Fallback to legacy selectors
                    if title == "N/A":
                        title_elem = await element.query_selector(".job-title")
                        title = await title_elem.inner_text() if title_elem else "N/A"
                    if company == "N/A":
                        company_elem = await element.query_selector(".company-name")
                        company = await company_elem.inner_text() if company_elem else "N/A"
                    
                    # Extract location
                    location_elem = await element.query_selector("span.ng-binding, .job-location")
                    job_location = await location_elem.inner_text() if location_elem else "N/A"
                    if "Job available in" in job_location:
                        job_location = job_location.replace("Job available in", "").strip()

                    # Extract URL
                    href = await element.get_attribute("href")
                    if href and not href.startswith("http"):
                        job_url = f"https://www.instahyre.com{href}"
                    else:
                        job_url = href or ""

                    # Extract description (snippet)
                    desc_elem = await element.query_selector("div:nth-child(2) > div:nth-child(4), .job-snippet")
                    description = await desc_elem.inner_text() if desc_elem else ""

                    if not job_url:
                        continue

                    # Generate ID
                    job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]

                    jobs.append({
                        "id": job_id,
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": job_location.strip(),
                        "url": job_url,
                        "description": description.strip(),
                        "portal": "instahyre"
                    })
                except Exception as inner_e:
                    print(f"Error parsing job card: {inner_e}")
                    continue

            return jobs

    except Exception as e:
        print(f"Playwright error scraping Instahyre: {e}")
        return []
    finally:
        if browser:
            await browser.close()

def fetch_jobs(roles: list[str] = None, location: str = "India") -> list[dict]:
    """
    Fetches jobs for multiple roles and deduplicates them.
    """
    if roles is None:
        roles = ["software engineer", "backend engineer", "python developer"]
    
    all_jobs = {}
    
    for i, role in enumerate(roles):
        if i > 0:
            print("Sleeping 3 seconds to avoid rate limiting...")
            time.sleep(3)
            
        try:
            results = asyncio.run(_scrape_instahyre(role, location))
            for job in results:
                if job["url"] not in all_jobs:
                    all_jobs[job["url"]] = job
        except Exception as e:
            print(f"Error fetching jobs for role '{role}': {e}")
            
    return list(all_jobs.values())

if __name__ == "__main__":
    jobs = fetch_jobs(["backend engineer"], "Bangalore")
    print(f"\nFound {len(jobs)} jobs:")
    for j in jobs[:3]:
        print(f"{j['title']} | {j['company']} | {j['location']}")
