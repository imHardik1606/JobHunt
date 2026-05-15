from scorer.key_pool import KeyPool
from scorer.multi_provider import score_job_with_pool

# Shared pool instance for sequential calls (like deep review)
_shared_pool = KeyPool()

def score_job(job_description: str) -> dict:
    """
    Compatibility wrapper for the old score_job function.
    Now uses the multi-provider key pool for rotation and reliability.
    """
    return score_job_with_pool(job_description, _shared_pool)

def batch_score_jobs(jobs: list[dict]) -> list[dict]:
    """
    Enriches a list of job dictionaries with AI scores sequentially.
    Note: For parallel processing, use scorer.parallel.score_jobs_parallel instead.
    """
    enriched_jobs = []
    total = len(jobs)
    
    for i, job in enumerate(jobs, 1):
        print(f"Scoring {i}/{total}: {job.get('title')} at {job.get('company')}...")
        result = score_job(job.get("description", ""))
        job["score_result"] = result
        job["score"] = result.get("score", 0)
        enriched_jobs.append(job)
        
    return enriched_jobs
