import os
import sqlite3
from typing import Union, List

# Database path
DB_PATH = "db/jobs.db"

def init_db():
    """
    Initializes the database and creates the jobs table if it doesn't exist.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT,
                description TEXT,
                portal TEXT,
                department TEXT,
                score REAL,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Simple migration: check if department column exists
        cursor = conn.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        if "department" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN department TEXT")
        
        if "score_json" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN score_json TEXT")
            
        conn.commit()

def save_jobs(jobs: List) -> int:
    """
    Saves a list of Job objects or dictionaries to the database.
    Skips duplicates using INSERT OR IGNORE.
    Returns the count of newly inserted rows.
    """
    if not jobs:
        return 0

    # Ensure we have a list of dictionaries for insertion
    data = []
    for job in jobs:
        if hasattr(job, "to_dict"):
            data.append(job.to_dict())
        elif isinstance(job, dict):
            data.append(job)
        else:
            print(f"⚠️ Warning: Unsupported job type {type(job)}")
            continue

    # Prepare specific columns for consistency
    params = [
        (
            item.get("id"),
            item.get("title"),
            item.get("company"),
            item.get("location"),
            item.get("url"),
            item.get("description"),
            item.get("portal"),
            item.get("department"),
            item.get("score")
        )
        for item in data
    ]

    with sqlite3.connect(DB_PATH) as conn:
        before = conn.total_changes
        conn.executemany("""
            INSERT OR IGNORE INTO jobs 
            (id, title, company, location, url, description, portal, department, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
        conn.commit()
        after = conn.total_changes
        return after - before

def get_new_jobs() -> List[dict]:
    """
    Returns all jobs with status = 'new', ordered by date.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status = 'new' ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

def get_all_jobs() -> List[dict]:
    """
    Returns all jobs in the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def update_status(job_id: str, status: str):
    """
    Updates the status of a specific job.
    Validates status against allowed values.
    """
    allowed_statuses = {"new", "reviewing", "applied", "rejected", "archived"}
    if status not in allowed_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {allowed_statuses}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()

def update_score(job_id: str, score: float):
    """
    Updates the numerical score for a specific job.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE jobs SET score = ? WHERE id = ?", (score, job_id))
        conn.commit()

def update_score_result(job_id: str, result: dict):
    """
    Updates both the numerical score and the full JSON result for a job.
    """
    import json
    score = result.get("score", 0)
    score_json = json.dumps(result)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE jobs SET score = ?, score_json = ? WHERE id = ?", 
            (score, score_json, job_id)
        )
        conn.commit()

def job_exists(job_id: str) -> bool:
    """
    Checks if a job with the given ID already exists.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT 1 FROM jobs WHERE id = ? LIMIT 1", (job_id,))
        return cursor.fetchone() is not None

def get_unscored_jobs() -> List[dict]:
    """
    Returns jobs with status = 'new' that haven't been scored yet.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status = 'new' AND score IS NULL ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

def get_jobs_by_status(status: str) -> List[dict]:
    """
    Returns all jobs with a specific status.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_jobs_by_score(min_score: float) -> List[dict]:
    """
    Returns all jobs with a score >= min_score, ordered by score DESC.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE score >= ? ORDER BY score DESC", (min_score,)
        )
        return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    # Internal test
    init_db()
    test_job = {
        "id": "test-123",
        "title": "Software Engineer",
        "company": "TestCorp",
        "location": "Remote",
        "url": "http://test.com",
        "description": "Blah blah",
        "portal": "ashby",
        "score": 8.5
    }
    inserted = save_jobs([test_job])
    print(f"Inserted {inserted} jobs.")
    print(f"Job exists? {job_exists('test-123')}")
    
    update_status("test-123", "reviewing")
    jobs = get_new_jobs()
    print(f"New jobs count: {len(jobs)}")
