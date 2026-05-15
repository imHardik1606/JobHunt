import asyncio
import hashlib
import time
from playwright.async_api import async_playwright
from scanner.base import Job

async def _scrape_page(url: str) -> list[dict]:
    """
    Scrapes a single page of YC Work at a Startup jobs using Playwright.
    """
    print(f"Scraping YC: {url}")
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
                # Wait for ANY job listings to load (public grid or user-provided list item)
                try:
                    await page.wait_for_selector(".jobs-list-item, a.text-base.font-semibold.text-blue-500", timeout=20000)
                except:
                    print(f"Timeout waiting for selectors at {url}, checking for elements anyway.")
                
                # Scroll to bottom to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"No jobs found or timeout at {url}: {e}")
                return []

            # Check for grid view (public) vs list view (likely logged-in)
            job_elements = await page.query_selector_all(".jobs-list-item")
            is_list_view = len(job_elements) > 0
            
            if not is_list_view:
                # Fallback to public grid view: find parents of title links
                titles = await page.query_selector_all("a.text-base.font-semibold.text-blue-500")
                job_elements = []
                for t in titles:
                    # The job card is typically a parent div
                    card = await t.evaluate_handle("el => el.closest('div.flex.flex-col') || el.parentElement")
                    job_elements.append(card)

            jobs = []

            for element in job_elements:
                try:
                    if is_list_view:
                        # User-provided selectors for list view
                        title_elem = await element.query_selector(".font-medium")
                        company_elem = await element.query_selector(".company-name")
                        location_elem = await element.query_selector(".location")
                        desc_elem = await element.query_selector(".job-description")
                        batch_elem = await element.query_selector(".batch")
                        link_elem = await element.query_selector("a")
                    else:
                        # Public grid view selectors
                        title_elem = await element.query_selector("a.text-base.font-semibold.text-blue-500")
                        company_elem = await element.query_selector("a.hover\\:underline, a[class*='hover:underline']")
                        location_elem = await element.query_selector("span") # Search within card for location-like text
                        desc_elem = None # Not easily available in grid view
                        batch_elem = company_elem
                        link_elem = title_elem

                    title = await title_elem.inner_text() if title_elem else "N/A"
                    company_text = await company_elem.inner_text() if company_elem else "N/A"
                    
                    # Parse batch from company text if needed (e.g. "Company (S23)")
                    batch = ""
                    company = company_text
                    if "(" in company_text and ")" in company_text:
                        import re
                        match = re.search(r"\(([^)]+)\)", company_text)
                        if match:
                            batch = match.group(1)
                            company = company_text.split("(")[0].strip()
                    
                    if is_list_view and batch_elem:
                        batch = await batch_elem.inner_text()

                    location = "Remote"
                    if not is_list_view:
                        # In public grid view, location is often in one of the spans
                        spans = await element.query_selector_all("span")
                        for span in spans:
                            text = await span.inner_text()
                            # Location usually contains a comma (city, country) or is "Remote"
                            if "," in text or "Remote" in text or "anywhere" in text.lower():
                                location = text.strip()
                                break
                    elif location_elem:
                        location = await location_elem.inner_text()
                    
                    href = await link_elem.get_attribute("href") if link_elem else ""
                    if href and not href.startswith("http"):
                        job_url = f"https://www.workatastartup.com{href}"
                    else:
                        job_url = href or ""

                    description = await desc_elem.inner_text() if desc_elem else ""

                    if not job_url:
                        continue

                    # Generate ID
                    job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]

                    jobs.append({
                        "id": job_id,
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": location.strip(),
                        "url": job_url,
                        "description": description.strip(),
                        "portal": "ycombinator",
                        "extra": {"yc_batch": batch.strip()}
                    })
                except Exception as inner_e:
                    print(f"Error parsing YC job item: {inner_e}")
                    continue

            return jobs

    except Exception as e:
        print(f"Playwright error scraping YC: {e}")
        return []
    finally:
        if browser:
            await browser.close()

def fetch_jobs(job_type: str = "both", remote_only: bool = False) -> list[dict]:
    """
    Fetches jobs from YC Work at a Startup and deduplicates them.
    job_type: "intern" | "fulltime" | "both"
    """
    urls = []
    if job_type in ["intern", "both"]:
        url = "https://www.workatastartup.com/jobs?role=eng&jobType=intern"
        if remote_only:
            url += "&remote=true"
        urls.append(url)
    
    if job_type in ["fulltime", "both"]:
        url = "https://www.workatastartup.com/jobs?role=eng&jobType=fulltime"
        if remote_only:
            url += "&remote=true"
        urls.append(url)

    all_jobs = {}
    
    print(f"Scanning YC Work at a Startup ({job_type})...")
    
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(3)
            
        try:
            results = asyncio.run(_scrape_page(url))
            for job in results:
                if job["url"] not in all_jobs:
                    all_jobs[job["url"]] = job
        except Exception as e:
            print(f"Error fetching YC jobs from {url}: {e}")
            
    final_list = list(all_jobs.values())
    print(f"Found {len(final_list)} listings")
    return final_list

def fetch_internships(remote_only: bool = False) -> list[dict]:
    """
    Convenience wrapper to fetch internships.
    """
    return fetch_jobs(job_type="intern", remote_only=remote_only)

if __name__ == "__main__":
    jobs = fetch_internships(remote_only=False)
    print(f"\nFound {len(jobs)} YC internships")
    for j in jobs[:5]:
        batch = j.get("extra", {}).get("yc_batch", "")
        print(f"  {j['title']} @ {j['company']} [{batch}] — {j['location']}")
