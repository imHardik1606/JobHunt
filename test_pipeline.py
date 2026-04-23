import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import project modules
import config
from db.store import init_db, save_jobs, job_exists, get_all_jobs
from scanner import greenhouse
from scorer.match import score_job
from tailor.resume import tailor_resume
from pdf.generator import generate_pdf
from tracker import sheets

console = Console()

def run_test_1():
    """TEST 1 — Config loads"""
    console.print("[bold cyan]TEST 1 — Config loads[/bold cyan]")
    try:
        is_valid = config.validate_config()
        if is_valid:
            console.print("✅ PASS: Config validated successfully.")
            return True
        else:
            console.print("❌ FAIL: Config validation failed.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Config loading crashed: {e}")
        return False

def run_test_2():
    """TEST 2 — Database initializes"""
    console.print("\n[bold cyan]TEST 2 — Database initializes[/bold cyan]")
    try:
        init_db()
        dummy_job = {
            "id": "dummy-test-id",
            "title": "Software Test Engineer",
            "company": "TestCorp",
            "location": "Virtual",
            "url": "https://test.com/jobs/1",
            "description": "Testing the pipeline",
            "portal": "test-portal",
            "score": 9.5
        }
        save_jobs([dummy_job])
        
        # Retrieve and verify
        all_jobs = get_all_jobs()
        retrieved = next((j for j in all_jobs if j['id'] == "dummy-test-id"), None)
        
        if retrieved and retrieved['title'] == dummy_job['title'] and retrieved['company'] == dummy_job['company']:
            console.print("✅ PASS: Database initialized and record verified.")
            return True
        else:
            console.print("❌ FAIL: Database retrieval mismatch or record not found.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Database test crashed: {e}")
        return False

def run_test_3():
    """TEST 3 — Greenhouse API reachable"""
    console.print("\n[bold cyan]TEST 3 — Greenhouse API reachable[/bold cyan]")
    try:
        jobs = greenhouse.fetch_jobs("Anthropic", "anthropic")
        if isinstance(jobs, list):
            console.print(f"✅ PASS: Greenhouse reachable. Found {len(jobs)} jobs for Anthropic.")
            return True
        else:
            console.print("❌ FAIL: Greenhouse fetch did not return a list.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Greenhouse API test failed: {e}")
        return False

def run_test_4():
    """TEST 4 — Gemini scoring works"""
    console.print("\n[bold cyan]TEST 4 — Gemini scoring works[/bold cyan]")
    try:
        test_jd = "Python backend engineer with REST APIs and Docker"
        result = score_job(test_jd)
        
        if "score" in result:
            score = result["score"]
            verdict = result.get("verdict", "N/A")
            console.print(f"Score: [bold green]{score}[/bold green], Verdict: {verdict}")
            if 0 <= score <= 10:
                console.print("✅ PASS: Gemini scoring returned valid score.")
                return True
            else:
                console.print(f"❌ FAIL: Score {score} out of range (0-10).")
                return False
        else:
            console.print("❌ FAIL: Result missing 'score' key.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Gemini scoring crashed: {e}")
        return False

def run_test_5():
    """TEST 5 — Resume tailoring works"""
    console.print("\n[bold cyan]TEST 5 — Resume tailoring works[/bold cyan]")
    try:
        # Read candidate name from cv.md
        candidate_name = "Candidate"
        if os.path.exists(config.CV_PATH):
            with open(config.CV_PATH, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                candidate_name = first_line.replace("#", "").strip()
        
        result = tailor_resume("Python backend role", "TestCo", "Backend Intern")
        
        if result and isinstance(result, str) and len(result) > 0:
            console.print(f"Preview: {result[:100]}...")
            if candidate_name.lower() in result.lower():
                console.print(f"✅ PASS: Resume tailored and contains candidate name '{candidate_name}'.")
                return True
            else:
                console.print(f"❌ FAIL: Tailored resume missing candidate name '{candidate_name}'.")
                return False
        else:
            console.print("❌ FAIL: Tailored resume is empty or not a string.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Resume tailoring crashed: {e}")
        return False

def run_test_6():
    """TEST 6 — PDF generation works"""
    console.print("\n[bold cyan]TEST 6 — PDF generation works[/bold cyan]")
    try:
        pdf_path = generate_pdf("# Test\n## Skills\n- Python", "TestCo", "Test Role")
        if pdf_path and os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            if file_size > 1000:
                console.print(f"✅ PASS: PDF generated at {pdf_path} ({file_size} bytes).")
                return True
            else:
                console.print(f"❌ FAIL: PDF file too small ({file_size} bytes).")
                return False
        else:
            console.print("❌ FAIL: PDF file not created.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: PDF generation crashed: {e}")
        return False

def run_test_7():
    """TEST 7 — Sheets configured (optional)"""
    console.print("\n[bold cyan]TEST 7 — Sheets configured (optional)[/bold cyan]")
    try:
        if not sheets.is_sheets_configured():
            console.print("[yellow]SKIP — Google Sheets not configured (optional)[/yellow]")
            return "SKIP"
        
        # Test logging a row
        test_job = {"company": "TestPipe", "title": "Pipeline Tester", "url": "https://test.com"}
        test_score = {"score": 10, "recommend_apply": True, "match_reasons": ["Auto-test"], "gaps": [], "verdict": "Testing"}
        
        success = sheets.log_application(test_job, test_score, notes="Automated pipeline test row")
        if success:
            console.print("✅ PASS: Logged test row to Google Sheets.")
            return True
        else:
            console.print("❌ FAIL: Google Sheets configuration valid but logging failed.")
            return False
    except Exception as e:
        console.print(f"❌ FAIL: Sheets test crashed: {e}")
        return False

def main():
    console.print(Panel("[bold green]JobHunt Pipeline Verification Script[/bold green]", expand=False))
    
    results = []
    
    results.append(run_test_1())
    results.append(run_test_2())
    results.append(run_test_3())
    results.append(run_test_4())
    results.append(run_test_5())
    results.append(run_test_6())
    results.append(run_test_7())
    
    # Calculate summary
    # SKIP doesn't count as FAIL for the "X/7 passed" metric if we want to be nice, 
    # but the user asked for "Results: 6/7 passed".
    # Let's count SKIP as not passed but not a failure in the count if it's optional.
    # Actually, the user's example "6/7 passed" implies 7 tests total.
    
    passed_count = sum(1 for r in results if r is True)
    total_count = len(results)
    
    color = "green" if passed_count == total_count else "yellow" if passed_count >= total_count - 1 else "red"
    
    console.print("\n" + "="*40)
    console.print(f"[{color} bold]Results: {passed_count}/{total_count} passed[/{color} bold]")
    console.print("="*40)

if __name__ == "__main__":
    main()
