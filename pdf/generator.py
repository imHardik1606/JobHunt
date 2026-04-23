import os
import re
import asyncio
import markdown
from playwright.async_api import async_playwright

TEMPLATE_PATH = "pdf/template.html"

def markdown_to_html(md_text: str) -> str:
    """
    Converts markdown text to HTML and wraps it in the resume template.
    Enhanced with regex to support Jake's Template split-header style.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"❌ Template file missing at {TEMPLATE_PATH}")
        
    # Convert MD to HTML
    body_html = markdown.markdown(md_text, extensions=['extra', 'smarty'])
    
    # Post-processing for Jake's Template split headers:
    # Find <h3>Text | Text | Date</h3> and transform to <h3>Text | Text <span>Date</span></h3>
    # This allows CSS flex-box to push the date to the right.
    def split_header(match):
        content = match.group(1)
        if "|" in content:
            parts = content.rsplit("|", 1)
            return f"<h3>{parts[0].strip()}<span>{parts[1].strip()}</span></h3>"
        return match.group(0)

    body_html = re.sub(r"<h3>(.*?)</h3>", split_header, body_html)

    # Load template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()
        
    # Inject content
    complete_html = template.replace("{{BODY}}", body_html)
    return complete_html

async def _render_pdf(html_content: str, output_path: str):
    """
    Internal async function to render HTML to PDF using Playwright.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set the content and wait for it to be stable
        await page.set_content(html_content, wait_until="networkidle")
        
        # Generate the PDF with Jake's Template margins (approx 0.5in)
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={
                "top": "0.5in",
                "right": "0.5in",
                "bottom": "0.5in",
                "left": "0.5in"
            }
        )
        
        await browser.close()

def generate_pdf(tailored_md: str, company: str, role: str) -> str:
    """
    Synchronous wrapper to generate a PDF from markdown.
    """
    try:
        import markdown
    except ImportError:
        print("❌ Error: 'markdown' package is not installed.")
        print("💡 Run: 'pip install markdown' to fix this.")
        return None

    try:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize and limit filename length
        clean_name = f"{company}_{role}"
        clean_name = re.sub(r"[^\w\s]", "", clean_name).replace(" ", "_")
        clean_name = clean_name[:60] # Limit length
        
        output_path = os.path.join(output_dir, f"{clean_name}.pdf")
        html = markdown_to_html(tailored_md)
        
        # Run the async renderer
        asyncio.run(_render_pdf(html, output_path))
        
        print(f"PDF saved: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        return None

if __name__ == "__main__":
    # Standalone test
    print("Testing PDF Generation...")
    sample_md = """# Test Name
## Summary
A results-driven backend engineer with 5 years of experience building scalable systems.

## Skills
- **Languages**: Python, SQL, Go
- **Tools**: Docker, Kubernetes, AWS

## Projects
### JobHunt Crawler
Built a job crawling system that handles 10k+ requests per minute.
"""
    try:
        path = generate_pdf(sample_md, "TestCompany", "Backend Engineer")
        print(f"Generated: {path}")
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: You might need to run 'playwright install chromium' first.")
