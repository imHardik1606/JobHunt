import os
import re
from google import genai
from config import GEMINI_API_KEY, CV_PATH

# Initialize Gemini Client
client = None
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in config. Resume tailoring will fail.")
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Use stable model
MODEL_NAME = "gemini-flash-latest"

def load_cv() -> str:
    """
    Reads the base CV from the configured markdown file.
    """
    if not os.path.exists(CV_PATH):
        raise FileNotFoundError(f"❌ Base CV file missing at {CV_PATH}.")
    
    with open(CV_PATH, "r", encoding="utf-8") as f:
        return f.read()

def tailor_resume(job_description: str, company: str, role: str) -> str:
    """
    Uses AI to tailor the CV for a specific job without fabricating experience.
    Returns the original CV unchanged if any error occurs.
    """
    base_cv = ""
    try:
        base_cv = load_cv()
    except:
        return ""

    if not client:
        print("⚠️ Warning: Gemini client not initialized. Returning original CV.")
        return base_cv

    try:
        jd_truncated = job_description[:3000]
        
        prompt = f"""You are an expert resume writer. Successfully tailor the candidate's CV for a specific job application.
The goal is to create a clean, Professional, and ATS-friendly PDF resume in the style of "Jake's Template".

YOUR RULES (follow strictly):
1. TRUTHFULNESS: NEVER add skills, experience, or achievements the candidate does not have.
2. RELEVANCE: Only reword and reorder existing content to highlight relevance to the JD.
3. EXPERIENCE VS PROJECTS: If the professional experience is low (e.g., student/intern), expand on the PROJECTS section significantly. Ensure the projects' tech stack and outcomes directly address the requirements in the JD.
4. KEYWORDS: Naturally inject primary keywords from the JD into project/experience bullets.
5. STRUCTURE: Use exactly this structure:
   - # [Full Name]
   - Contact Info Line (Email | Phone | LinkedIn | GitHub | Website)
   - ## EDUCATION (Degree, College, GPA, Dates)
   - ## EXPERIENCE (If any. Professional roles)
   - ## PROJECTS (Highlight tech stack and impact)
   - ## TECHNICAL SKILLS (Categorized: Languages, Backend, Tools, etc.)
   - ## ACHIEVEMENTS

FORMATTING:
- Use ### **Name** | [Details] | [Location] | [Dates] for all items in Education/Experience/Projects.
- Use bullet points for all details.

HUMANIZATION RULES:
- Vary sentence structure. Not every bullet starts with "Designed", "Built", "Implemented".
  Use: developed, shipped, debugged, refactored, owned, led, reduced, improved, cut, enabled
- Avoid buzzword stacking. "Leveraged cutting-edge scalable microservices" → never write this.
- Use specific numbers where they exist in the original CV. Do not invent numbers.
- Write bullets as outcomes, not task descriptions.
  Bad: "Implemented caching layer using Redis"
  Good: "Cut API response time by ~60% by adding Redis caching to hot query paths"
- One bullet = one idea. No compound bullets joined by semicolons.
- Max 2 bullets per project that start with the same verb.
- The summary paragraph (if any) should sound like the candidate wrote it themselves, not like a recruiter wrote it. First person implied, not stated.
- Do not use: "leverage", "spearhead", "synergy", "cutting-edge", "passionate about", "results-driven", "detail-oriented", "fast-paced environment"
- Do use: plain language, concrete actions, real outcomes

TARGET COMPANY: {company}
TARGET ROLE: {role}

JOB DESCRIPTION:
{jd_truncated}

ORIGINAL CV:
{base_cv}

Return the complete tailored CV in Markdown format. Ensure it feels premium and targeted.

SELF-CHECK:
Review your output. If any bullet starts with 'Leveraged', rewrite it.
If two consecutive bullets have the same opening verb, rewrite one.
If the summary contains 'passionate', rewrite it.
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        
        return response.text.strip()

    except Exception as e:
        print(f"⚠️ Warning: Error tailoring resume: {e}. Returning original CV.")
        return base_cv

def save_tailored_cv(content: str, company: str, role: str) -> str:
    """
    Saves the tailored markdown to the output/ directory with a sanitized filename.
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Sanitize company and role for filename
    clean_company = re.sub(r"[^\w\s]", "", company).replace(" ", "_")
    clean_role = re.sub(r"[^\w\s]", "", role).replace(" ", "_")
    
    filename = f"{clean_company}_{clean_role}_tailored.md"
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return file_path

if __name__ == "__main__":
    # Standalone test
    print(f"Testing Resume Tailoring ({MODEL_NAME})...")
    result = tailor_resume(
        "We need a backend engineer with Python, FastAPI, and Docker experience.",
        "TestCo",
        "Backend Engineer Intern"
    )
    print("\n--- Tailored CV Preview ---")
    print(result[:500])
    
    if result:
        saved_path = save_tailored_cv(result, "TestCo", "Backend Engineer Intern")
        print(f"\nSaved tailored CV to: {saved_path}")
