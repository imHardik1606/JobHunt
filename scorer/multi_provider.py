import os
import json
import re
import requests
import google.genai as genai
from typing import Optional, Dict
from scorer.key_pool import KeyPool, Key

# Module-level cache for CV content
_cv_cache = None

SCORING_PROMPT = """
You are a technical recruiter evaluating a candidate's fit for a job.

CANDIDATE CV:
{cv}

JOB DESCRIPTION:
{jd}

Return ONLY valid JSON with no markdown fences, no explanation, nothing else.
Exact structure required:
{{
  "score": <float 0.0-10.0>,
  "grade": <"A"|"B"|"C"|"D"|"F">,
  "verdict": "<one sentence max>",
  "match_reasons": ["<specific reason 1>", "<specific reason 2>", "<specific reason 3>"],
  "gaps": ["<specific gap 1>", "<specific gap 2>"],
  "top_project": "<name of candidate's most relevant project for this JD>",
  "recommend_apply": <true|false>,
  "effort_to_apply": <"low"|"medium"|"high">
}}

Grade mapping: A=8-10 (strong match), B=6-7 (good), C=5 (borderline), D=3-4 (weak), F=0-2 (skip)
effort_to_apply: low=minor tweaks needed, medium=significant tailoring, high=major gaps
"""

ERROR_RESULT = {
    "score": 0.0,
    "grade": "F",
    "verdict": "Could not parse AI response",
    "match_reasons": [],
    "gaps": ["Scoring failed — will retry on next scan"],
    "top_project": "",
    "recommend_apply": False,
    "effort_to_apply": "high"
}

def load_cv() -> str:
    """Reads and caches the cv.md file from project root."""
    global _cv_cache
    if _cv_cache is not None:
        return _cv_cache
    
    cv_path = "cv.md"
    if not os.path.exists(cv_path):
        raise FileNotFoundError("cv.md not found. Create it in project root and paste your CV in markdown.")
    
    with open(cv_path, "r", encoding="utf-8") as f:
        _cv_cache = f.read().strip()
    return _cv_cache

def _call_gemini(key: Key, prompt: str) -> str:
    """Calls Gemini API using the official SDK."""
    genai.configure(api_key=key.api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": 1000}
    )
    return response.text

def _call_groq(key: Key, prompt: str) -> str:
    """Calls Groq API via direct HTTP request."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key.api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def _call_openrouter(key: Key, prompt: str) -> str:
    """Calls OpenRouter API using the 'openrouter/free' meta-model."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/imHardik1606/jobhunt",
        "X-Title": "JobHunt"
    }
    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def _parse_response(text: str) -> dict:
    """Robustly parses JSON from LLM output with validation."""
    clean_text = text.strip()
    # Remove markdown fences
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    
    clean_text = clean_text.strip()
    
    try:
        result = json.loads(clean_text)
    except json.JSONDecodeError:
        # Try regex extraction for fallback
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
            except json.JSONDecodeError:
                print(f"[Scorer] Parse failed: {text[:200]}")
                return ERROR_RESULT
        else:
            print(f"[Scorer] Parse failed: {text[:200]}")
            return ERROR_RESULT
            
    # Validation
    if "score" not in result or not isinstance(result["score"], (int, float)):
        print(f"[Scorer] Validation failed (missing/invalid score): {text[:200]}")
        return ERROR_RESULT
        
    if not (0 <= result["score"] <= 10):
        print(f"[Scorer] Validation failed (score out of range): {result['score']}")
        return ERROR_RESULT
        
    return result

PROVIDER_CALLERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
    "openrouter": _call_openrouter,
}

def score_job_with_pool(job_description: str, pool: KeyPool) -> dict:
    """
    Unified scoring function that uses the KeyPool for rotation and handles 429s.
    """
    try:
        cv = load_cv()
    except Exception as e:
        print(f"[Scorer] Error: {str(e)}")
        return ERROR_RESULT
        
    # Truncate JD to avoid token limits
    jd = job_description[:3000]
    prompt = SCORING_PROMPT.format(cv=cv, jd=jd)
    
    key = pool.wait_for_key(timeout=120)
    if not key:
        print("[Scorer] No API key available after 120s")
        return ERROR_RESULT
        
    caller = PROVIDER_CALLERS.get(key.provider)
    if not caller:
        return ERROR_RESULT
        
    try:
        raw = caller(key, prompt)
        pool.mark_used(key)
        return _parse_response(raw)
        
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            pool.mark_error(key, is_rate_limit=True)
            print(f"[Scorer] Rate limited on {key.provider}. Retrying with different key...")
            
            # Retry once with a different key
            key2 = pool.wait_for_key(timeout=60)
            if key2:
                try:
                    raw2 = PROVIDER_CALLERS[key2.provider](key2, prompt)
                    pool.mark_used(key2)
                    return _parse_response(raw2)
                except Exception as inner_e:
                    pool.mark_error(key2)
                    print(f"[Scorer] Retry failed on {key2.provider}: {str(inner_e)}")
                    return ERROR_RESULT
            return ERROR_RESULT
        else:
            pool.mark_error(key)
            print(f"[Scorer] HTTP error {e.response.status_code if e.response else 'unknown'} on {key.provider}")
            return ERROR_RESULT
            
    except Exception as e:
        # Handle provider-specific rate limit errors (e.g. Gemini SDK)
        if "429" in str(e) or "quota" in str(e).lower():
            pool.mark_error(key, is_rate_limit=True)
            print(f"[Scorer] Rate limited (Exception) on {key.provider}. Retrying...")
            # Simple recursive retry for the first fallback
            key2 = pool.wait_for_key(timeout=60)
            if key2:
                 try:
                    raw2 = PROVIDER_CALLERS[key2.provider](key2, prompt)
                    pool.mark_used(key2)
                    return _parse_response(raw2)
                 except Exception:
                    pool.mark_error(key2)
                    return ERROR_RESULT
        else:
            pool.mark_error(key)
            print(f"[Scorer] Unexpected error on {key.provider}: {str(e)}")
            
        return ERROR_RESULT

if __name__ == "__main__":
    # Test block
    from scorer.key_pool import KeyPool
    import json
    
    # Initialize pool
    pool = KeyPool()
    
    print("\n[Test] Scoring sample job description...")
    test_jd = (
        "Backend engineer with Python, FastAPI, Docker, and PostgreSQL experience. "
        "Will work on REST APIs and async job processing pipelines."
    )
    
    result = score_job_with_pool(test_jd, pool)
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    print(f"\nFinal Pool Status: {pool.status()}")
