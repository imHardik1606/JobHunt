import concurrent.futures
import threading
from rich import print
from rich.progress import Progress
from scorer.key_pool import KeyPool
from scorer.multi_provider import score_job_with_pool
from db.store import update_score, update_score_result

def score_single_job(job: dict, pool: KeyPool, progress: Progress = None, task_id: int = None) -> dict:
    """
    Scores one job using the key pool, updates the database, and updates the progress bar.
    """
    try:
        # We use score_job_with_pool which handles provider rotation and retries internally
        result = score_job_with_pool(job["description"], pool)
        
        # Update database with the score result
        # We use update_score_result to save the full JSON as well, 
        # which is expected by other parts of the app.
        update_score_result(job["id"], result)
        
        if progress and task_id is not None:
            progress.advance(task_id)
            
        return {
            "job_id": job["id"], 
            "success": True, 
            "score": result["score"],
            "grade": result["grade"], 
            "company": job["company"], 
            "title": job["title"]
        }
    except Exception as e:
        return {
            "job_id": job["id"], 
            "success": False, 
            "error": str(e),
            "company": job["company"], 
            "title": job["title"]
        }

def get_optimal_worker_count(pool: KeyPool) -> int:
    """
    Calculates safe parallel worker count based on available keys.
    Rule: min(available_keys * 2, 6).
    """
    status = pool.status()
    total_available = sum(v["available"] for v in status.values())
    return min(max(total_available * 2, 1), 6)

def score_jobs_parallel(jobs: list[dict], max_workers: int = None) -> dict:
    """
    Scores multiple jobs in parallel using ThreadPoolExecutor and key rotation.
    Returns a summary of the scoring run.
    """
    if not jobs:
        return {"total": 0, "success": 0, "failed": 0, "results": []}

    pool = KeyPool()
    
    # Auto-calculate workers if not provided
    if max_workers is None:
        max_workers = get_optimal_worker_count(pool)

    # Print key pool status before starting
    print("\n[bold blue]Starting parallel scoring pipeline...[/]")
    status = pool.status()
    for provider, info in status.items():
        print(f"  {provider}: {info['available']} keys available")

    results = []
    failed = []

    with Progress() as progress:
        task = progress.add_task(
            f"[cyan]Scoring {len(jobs)} jobs across {max_workers} workers...",
            total=len(jobs)
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(score_single_job, job, pool, progress, task): job
                for job in jobs
            }

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result["success"]:
                    results.append(result)
                    # Print inline result using rich progress console
                    grade = result["grade"]
                    color = {
                        "A": "green", 
                        "B": "bright_green", 
                        "C": "yellow", 
                        "D": "red", 
                        "F": "dim"
                    }.get(grade, "white")
                    
                    progress.console.print(
                        f"  [{color}]{grade}[/] {result['score']}/10 - {result['title']} at {result['company']}"
                    )
                else:
                    failed.append(result)
                    progress.console.print(
                        f"  [red][FAILED][/] {result['title']} at {result['company']} - {result.get('error','')}"
                    )

    return {
        "total": len(jobs),
        "success": len(results),
        "failed": len(failed),
        "results": results,
        "failed_jobs": failed
    }
