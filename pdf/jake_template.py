import os
import re
import asyncio
import subprocess
import markdown
from playwright.async_api import async_playwright

JAKE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Resume</title>
    <style>
        @page {
            size: letter;
            margin: 0.5in;
        }
        body {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10pt;
            line-height: 1.2;
            color: black;
            margin: 0;
            padding: 0;
        }
        h1 {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 28pt;
            text-align: center;
            margin: 0 0 5px 0;
            font-weight: bold;
        }
        .contact-info {
            text-align: center;
            font-size: 9pt;
            margin-bottom: 15px;
        }
        h2 {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 12pt;
            text-transform: uppercase;
            border-bottom: 1px solid black;
            margin: 15px 0 5px 0;
            padding-bottom: 2px;
            font-weight: bold;
        }
        h3 {
            font-size: 10pt;
            margin: 8px 0 2px 0;
            display: flex;
            justify-content: space-between;
            font-weight: bold;
        }
        h3 span {
            font-weight: normal;
        }
        h4 {
            font-size: 10pt;
            margin: 2px 0 2px 0;
            font-style: italic;
            font-weight: normal;
            display: flex;
            justify-content: space-between;
        }
        ul {
            margin: 3px 0 8px 0;
            padding-left: 15px;
            list-style-type: none;
        }
        li {
            margin-bottom: 2px;
            position: relative;
        }
        li::before {
            content: "—";
            position: absolute;
            left: -15px;
        }
        p {
            margin: 5px 0;
        }
        strong {
            font-weight: bold;
        }
        em {
            font-style: italic;
        }
        a {
            color: black;
            text-decoration: none;
        }
        @media print {
            body {
                -webkit-print-color-adjust: exact;
            }
        }
    </style>
</head>
<body>
    {{BODY}}
</body>
</html>
"""

def markdown_to_jake_html(md_text: str) -> str:
    """
    Converts markdown to Jake's Resume style HTML.
    Assumes first H1 is the name and subsequent text is contact info.
    """
    # Convert MD to HTML
    body_html = markdown.markdown(md_text, extensions=['extra', 'smarty'])
    
    # Process headers for Date-to-the-right (Text | Date or Text | Text | Date)
    def split_header(match):
        content = match.group(1)
        if "|" in content:
            parts = [p.strip() for p in content.split("|")]
            if len(parts) >= 2:
                main_text = " | ".join(parts[:-1])
                date_text = parts[-1]
                return f"<h3>{main_text}<span>{date_text}</span></h3>"
        return match.group(0)

    body_html = re.sub(r"<h3>(.*?)</h3>", split_header, body_html)
    
    # Optional: support h4 for sub-headers with dates
    def split_sub_header(match):
        content = match.group(1)
        if "|" in content:
            parts = [p.strip() for p in content.split("|")]
            return f"<h4>{parts[0]}<span>{parts[1]}</span></h4>"
        return match.group(0)
    
    body_html = re.sub(r"<h4>(.*?)</h4>", split_sub_header, body_html)

    # Wrap in template
    return JAKE_HTML_TEMPLATE.replace("{{BODY}}", body_html)

async def _render_jake_pdf(html_content: str, output_path: str):
    """Internal async playwright renderer."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        
        await page.pdf(
            path=output_path,
            format="Letter",
            margin={
                "top": "0.5in",
                "right": "0.5in",
                "bottom": "0.5in",
                "left": "0.5in"
            },
            print_background=False
        )
        await browser.close()

def generate_jake_pdf(tailored_md: str, company: str, role: str) -> str:
    """
    Generates a Jake's style PDF resume.
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Sanitize filename
    clean_name = f"{company}_{role}_Jake"
    clean_name = re.sub(r"[^\w\s]", "", clean_name).replace(" ", "_")
    clean_name = clean_name[:60]
    
    output_path = os.path.join(output_dir, f"{clean_name}.pdf")
    
    # Check LaTeX for the tip
    if check_latex_available():
        print("💡 Tip: LaTeX is available. Future versions can use native .tex compilation.")
    
    # Convert and Render
    html = markdown_to_jake_html(tailored_md)
    asyncio.run(_render_jake_pdf(html, output_path))
    
    print(f"[Jake Resume] PDF saved: {output_path}")
    return output_path

def check_latex_available() -> bool:
    """Checks if pdflatex is installed on the system."""
    try:
        subprocess.run(["pdflatex", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

if __name__ == "__main__":
    # Test
    test_md = """# HARDIK M.
[hardik.dev](https://hardik.dev) | hardik@example.com | +91 9876543210 | [LinkedIn](https://linkedin.com) | [GitHub](https://github.com)

## EDUCATION
### College of Engineering | Bachelor of Computer Applications | July 2023 – July 2026

## EXPERIENCE
### Tech Startup | Backend Intern | May 2024 – Present
- Built a RAG pipeline using Gemini and Pinecone for automated document analysis
- Optimized API latency by 40% using Redis caching and asynchronous processing
- Developed a job tracking system using Python and SQLite

## PROJECTS
### JobHunt Assistant | Python, Gemini, SQLite | Jan 2024
- Created an automated job discovery and application tailoring system
- Implemented real-time scoring of job descriptions against candidate CVs
"""
    generate_jake_pdf(test_md, "Test", "Developer")
