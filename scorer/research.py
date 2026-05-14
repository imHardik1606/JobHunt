import os
import time
from google import genai
from config import GEMINI_API_KEY

def load_file(path: str) -> str:
    """
    Read and return file contents as string.
    If file doesn't exist: return empty string, print warning.
    """
    if not os.path.exists(path):
        print(f"Warning: File not found at {path}")
        return ""
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read file at {path}: {e}")
        return ""

def build_outreach_prompt(company: str, role: str) -> str:
    """
    Build and return a combined prompt string for outreach research.
    """
    research_instr = load_file("modes/outreach_research.md")
    cv_content = load_file("cv.md")
    
    prompt = f"""=== YOUR TASK ===
{research_instr}

=== CANDIDATE CV ===
{cv_content}

=== TARGET ===
Company: {company}
Role: {role}

Generate the complete outreach research package for this specific company and role."""
    
    return prompt

def run_outreach_research(company: str, role: str) -> str:
    """
    Configure Gemini and generate outreach research content using the modern SDK.
    Implements a single retry for rate limits.
    """
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not set in config."

    # Use the same modern client setup as match.py
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_NAME = "gemini-flash-latest"
    prompt = build_outreach_prompt(company, role)
    
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            # Check for rate limit (429)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt == 0:
                    print("Rate limit hit. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                else:
                    return f"Outreach research failed due to persistent rate limits: {error_msg}"
            
            print(f"Error during outreach research: {error_msg}")
            return "Outreach research failed. Check your API key and modes/outreach_research.md file."

def save_outreach_report(content: str, company: str, role: str) -> str:
    """
    Save the generated outreach report to the reports/ directory.
    """
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # Sanitize filename
    safe_company = company.replace(" ", "_")
    safe_role = role.replace(" ", "_")
    filename = f"outreach_{safe_company}_{safe_role}.md"
    filepath = os.path.join(reports_dir, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
    except Exception as e:
        print(f"Error saving report: {e}")
        return ""

def extract_sincerely_templates(outreach_content: str, company: str, role: str) -> str:
    """
    Parse the outreach research output and extract only the Sincerely templates section.
    Save them to output/sincerely_{company}_{role}.md
    Return the file path.
    """
    # Find content between "SINCERELY TEMPLATE" markers
    import re
    templates = re.findall(
        r'--- SINCERELY TEMPLATE:.*?--- END TEMPLATE ---',
        outreach_content,
        re.DOTALL
    )

    if not templates:
        # Fallback: return the full outreach content if no markers found
        templates = [outreach_content]

    os.makedirs("output", exist_ok=True)
    filename = f"sincerely_{company}_{role}".replace(" ", "_")[:60]
    path = f"output/{filename}.md"

    content = f"# Sincerely Templates — {company} | {role}\n"
    content += f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    content += "## HOW TO USE\n"
    content += "1. Install Sincerely from Chrome Web Store\n"
    content += "2. Open Gmail → Compose → Click Sincerely icon\n"
    content += "3. Create new template → paste Subject and Body\n"
    content += "4. Always replace [FIRSTNAME] before sending\n"
    content += "5. Send ONE at a time. Review every message before hitting send.\n\n---\n\n"
    content += "\n\n---\n\n".join(templates)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
