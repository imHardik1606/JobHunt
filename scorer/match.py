import os
import json
import time
import re
from google import genai
from config import GEMINI_API_KEY, CV_PATH

# Initialize Gemini Client
client = None
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in config. AI scoring will fail.")
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Use stable model
MODEL_NAME = "gemini-flash-latest"

def load_cv() -> str:
    """
    Reads the candidate's CV from the configured markdown file.
    """
    if not os.path.exists(CV_PATH):
        raise FileNotFoundError(f"❌ CV file missing at {CV_PATH}. Please create it first.")
    
    with open(CV_PATH, "r", encoding="utf-8") as f:
        return f.read()

def score_job(job_description: str) -> dict:
    """
    Scores a single job description against the candidate's CV using Gemini (google-genai SDK).
    Implements 3x retry and regex fallback for JSON extraction.
    """
    if not client:
        return {"score": 0, "gaps": ["API Client not initialized"], "recommend_apply": False}

    cv_text = ""
    try:
        cv_text = load_cv()
    except Exception as e:
        return {"score": 0, "gaps": [f"CV Load failed: {e}"], "recommend_apply": False}

    jd_truncated = job_description[:3000]
    
    prompt = f"""You are a technical recruiter. Evaluate the candidate's fit for this job.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{jd_truncated}

EVALUATION RULES:
1. If the candidate has limited professional experience, prioritize their PROJECTS and TECHNICAL SKILLS.
2. Check if the tools, languages, and architectures used in their PROJECTS match the JD's requirements.
3. Be generous with the score if the projects demonstrate high complexity and relevant tech stack (e.g., LLMs, RAG, Async APIs).

Return ONLY valid JSON with no markdown formatting, no explanation, no code blocks.
Use exactly this structure:
{{
  "score": <number 0.0 to 10.0>,
  "match_reasons": ["reason1", "reason2", "reason3"],
  "gaps": ["gap1", "gap2"],
  "verdict": "one sentence summary of fit",
  "recommend_apply": <true or false>
}}

Score guide: 8-10 strong match, 6-7 good match, 4-5 partial, 0-3 skip."""

    last_error = ""
    last_raw_response = ""

    for attempt in range(1, 6): # Increased to 5 attempts
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            
            raw_text = response.text.strip()
            last_raw_response = raw_text
            
            # 1. Try stripping code fences
            clean_text = raw_text
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "", 1)
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()
            
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError:
                # 2. Try regex extraction if direct parse fails
                match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                else:
                    raise ValueError("No JSON object found in response.")

        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            
            # Smart Rate Limit Handling (429 Errors)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                # Try to extract wait time from message (e.g., "Please retry in 36s")
                wait_time = 30 # Default wait
                match = re.search(r"retry in ([\d\.]+)s", error_msg)
                if match:
                    wait_time = float(match.group(1)) + 2 # Add buffer
                
                print(f"\n⚠️  Rate limit hit. Pausing for {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            
            # Other errors: standard backoff
            if attempt < 5:
                time.sleep(5 * attempt)
            continue
            
    # Final failure
    print(f"❌ Final scoring failure after 3 attempts: {last_error}")
    print(f"DEBUG: Raw response: {last_raw_response}")
    
    return {
        "score": 0,
        "match_reasons": [],
        "gaps": [f"Scoring failed after 3 attempts: {last_error}"],
        "verdict": "Could not evaluate",
        "recommend_apply": False
    }

def batch_score_jobs(jobs: list[dict]) -> list[dict]:
    """
    Enriches a list of job dictionaries with AI scores.
    """
    total = len(jobs)
    enriched_jobs = []
    
    for i, job in enumerate(jobs, 1):
        job_title = job.get("title", "Unknown Role")
        company = job.get("company", "Unknown Company")
        
        print(f"Scoring {i}/{total}: {job_title} at {company}...")
        
        score_result = score_job(job.get("description", ""))
        job["score_result"] = score_result
        job["score"] = score_result.get("score", 0)
        
        enriched_jobs.append(job)
        
        if i < total:
            time.sleep(2)
            
    return enriched_jobs

if __name__ == "__main__":
    # Standalone test
    print(f"Testing AI Scorer ({MODEL_NAME})...")
    test_jd = "We need a Python backend engineer with REST API experience and Docker knowledge."
    result = score_job(test_jd)
    print(json.dumps(result, indent=2))
