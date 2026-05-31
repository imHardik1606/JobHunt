import sys
import os
import webbrowser
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress
from rich.prompt import Prompt, Confirm

# Project Imports
from scanner import scan_all, matches_experience
from scorer.match import score_job
from tailor.resume import tailor_resume, save_tailored_cv
from pdf.generator import generate_pdf
from tracker.sheets import log_application, is_configured, print_setup_instructions
from db.store import (
    init_db, save_jobs, get_new_jobs, update_status, 
    update_score, update_score_result, get_unscored_jobs, get_jobs_by_status, get_all_jobs,
    get_jobs_by_score, get_job_by_id
)
from config import MIN_SCORE_TO_SHOW, validate_config, get_department_keywords, DEPARTMENTS, get_experience_keywords
from scorer.research import run_outreach_research, save_outreach_report

console = Console()

def cmd_scan():
    """
    Scans portals for new jobs and scores them using AI.
    Usage: python main.py scan [dept] [flags]
    """
    args = set(arg.lower() for arg in sys.argv[2:])
    
    EXPERIENCE_FLAGS = {"fresher", "intern", "junior", "mid", "senior", "any"}
    COUNTRY_FLAGS = {"india", "remote"}
    PORTAL_FLAGS = {"yc"}

    experience = next((a for a in args if a in EXPERIENCE_FLAGS), "fresher")
    country    = next((a for a in args if a in COUNTRY_FLAGS), None)
    include_yc = "yc" in args
    department = next((a for a in args if a not in
                       EXPERIENCE_FLAGS | COUNTRY_FLAGS | PORTAL_FLAGS), "engineering")
    
    include_indian_portals = "india" in args
    
    try:
        # Validate department and get keywords to ensure it exists
        get_department_keywords(department)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        return

    header_parts = [
        f"Scanning [{department.upper()}]",
        f"Level: {experience.upper()}"
    ]
    if include_yc:
        header_parts.append("YC: ON")
    if country:
        header_parts.append(f"Location: {country.title()}")
    
    header_msg = "[bold blue]" + " | ".join(header_parts) + "[/]"
    console.print(Panel(header_msg, expand=False))
    
    jobs = scan_all(
        department=department, 
        experience=experience,
        country=country, 
        include_yc=include_yc, 
        include_indian_portals=include_indian_portals
    )
    if not jobs:
        console.print("\n[bold red]No jobs found.[/]")
        console.print("TIP: Troubleshooting: Check your internet connection or verify that company IDs in [bold]config.py[/] are correct.")
        return

    inserted = save_jobs(jobs)
    skipped = len(jobs) - inserted
    
    console.print(f"OK: Found {len(jobs)} total jobs. [green]{inserted} new[/], [yellow]{skipped} skipped (duplicates)[/].")
    
    unscored = get_unscored_jobs()
    if not unscored:
        console.print("[bold green]All jobs already scored.[/]")
        return
    
    # Pre-filtering based on Keywords to save AI tokens and time
    keywords = get_department_keywords(department)
    from config import NEGATIVE_KEYWORDS
    to_score = []
    skipped_count = 0
    
    for job in unscored:
        title_lower = job["title"].lower()
        
        # 1. Check for negative keywords first (Exclude Senior/Lead)
        if any(nk.lower() in title_lower for nk in NEGATIVE_KEYWORDS):
            update_status(job["id"], "archived")
            skipped_count += 1
            continue

        # 2. Check for positive keywords (Include relevant roles)
        if any(kw.lower() in title_lower for kw in keywords):
            to_score.append(job)
        else:
            # Silently archive irrelevant roles
            update_status(job["id"], "archived")
            skipped_count += 1

    if skipped_count > 0:
        console.print(f"INFO: [dim]Automatically archived {skipped_count} irrelevant roles (Sales, HR, etc.) based on keywords.[/]")

    if not to_score:
        console.print("[bold green]No relevant new jobs found for your keywords.[/]")
        return
        
    console.print(f"\n[bold]Scoring {len(to_score)} jobs...[/]")

    # Use the new parallel scoring pipeline with key rotation
    from scorer.parallel import score_jobs_parallel, get_optimal_worker_count
    from scorer.key_pool import KeyPool

    try:
        pool = KeyPool()
        workers = get_optimal_worker_count(pool)
        console.print(f"[dim]Using {workers} parallel workers across available API keys[/]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        return

    # Run parallel scoring
    summary = score_jobs_parallel(to_score, max_workers=workers)

    # Print summary
    console.print(f"\n[bold]Scoring complete:[/]")
    console.print(f"  [green][SUCCESS] Scored: {summary['success']}/{summary['total']}[/]")
    if summary['failed'] > 0:
        console.print(f"  [red][FAILED] Failed: {summary['failed']}[/]")
        console.print(f"  [dim]Failed jobs will be retried on next scan[/]")
    
    console.print("\n[bold green]Scan complete![/] Run [cyan]'python main.py review'[/] to see high-potential leads.")

def cmd_internships():
    """
    Search YC internships only.
    Usage: python main.py internships [india|remote]
    """
    location = sys.argv[2].lower() if len(sys.argv) > 2 else None
    
    console.print("[bold blue]Searching YC internships...[/]")
    
    from scanner.ycombinator import fetch_internships_only, fetch_yc_company_internships
    
    # Fetch from both sources
    waas_jobs = fetch_internships_only(location_hint=location)
    yc_jobs = fetch_yc_company_internships()
    
    # Combine and deduplicate by URL
    all_raw_jobs = waas_jobs + yc_jobs
    seen_urls = set()
    combined_jobs = []
    for job in all_raw_jobs:
        url = job.get("url")
        if url not in seen_urls:
            seen_urls.add(url)
            combined_jobs.append(job)
            
    # Filter by experience level "intern" using matches_experience()
    exp_keywords = get_experience_keywords("intern")
    filtered_jobs = [
        job for job in combined_jobs
        if matches_experience(job, exp_keywords)
    ]
    
    # Save to DB
    inserted = save_jobs(filtered_jobs)
    skipped = len(filtered_jobs) - inserted
    console.print(f"OK: Found {len(filtered_jobs)} total internships. [green]{inserted} new[/], [yellow]{skipped} skipped (duplicates)[/].")
    
    # Score with score_jobs_parallel
    unscored = get_unscored_jobs()
    saved_ids = {j["id"] for j in filtered_jobs}
    to_score = [j for j in unscored if j["id"] in saved_ids]
    
    if to_score:
        from scorer.parallel import score_jobs_parallel, get_optimal_worker_count
        from scorer.key_pool import KeyPool
        try:
            pool = KeyPool()
            workers = get_optimal_worker_count(pool)
            score_jobs_parallel(to_score, max_workers=workers)
        except Exception as e:
            console.print(f"[red]Scoring failed: {e}[/]")
    else:
        console.print("[bold green]All jobs already scored.[/]")
        
    # Show results directly in pipeline view filtered to these jobs
    cmd_pipeline(jobs_list=filtered_jobs, min_score=0.0)
    
    # Print footer
    console.print(f"\nFound {len(filtered_jobs)} internships across YC portfolio + Work at a Startup")

def cmd_review(department=None):
    """
    Interactive review of high-scoring job leads.
    """
    while True:
        all_new = get_new_jobs()
        
        # Filter by department if specified
        if department:
            all_new = [j for j in all_new if j.get("department") == department]
            
        # Filter by minimum score
        high_potential = [j for j in all_new if (j.get("score") or 0) >= MIN_SCORE_TO_SHOW and j.get("status") == "new"]
        
        if not high_potential:
            msg = f"No pending high-potential {department.upper() if department else ''} jobs found"
            console.print(f"\n[bold yellow]{msg} (Score >= {MIN_SCORE_TO_SHOW}).[/]")
            console.print(f"Try running [cyan]'python main.py scan {department if department else ''}'[/] to find more roles.")
            return

        # Sort by score descending
        high_potential.sort(key=lambda x: x.get("score") if x.get("score") is not None else 0, reverse=True)

        title = f"JobHunt Opportunity Dashboard {f'({department.upper()})' if department else ''}"
        table = Table(title=title, box=None, header_style="bold blue")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Match", justify="center")
        table.add_column("Grade", justify="center")
        table.add_column("Company", style="bold")
        table.add_column("Role", style="white")
        table.add_column("Portal", style="dim")

        for i, job in enumerate(high_potential, 1):
            score = job.get("score") if job.get("score") is not None else 0
            score_style = "green" if score >= 8 else "yellow" if score >= 6 else "red"
            
            # Extract grade from score_json if available
            grade = "N/A"
            if job.get("score_json"):
                try:
                    import json
                    analysis = json.loads(job["score_json"])
                    grade = analysis.get("grade", "N/A")
                except: pass
            
            grade_style = "bold green" if grade == "A" else "green" if grade == "B" else "yellow" if grade == "C" else "red"

            table.add_row(
                str(i),
                f"[{score_style}]{score*10:.0f}%[/]",
                f"[{grade_style}]{grade}[/]",
                job["company"],
                job["title"],
                job["portal"]
            )

        console.print("\n")
        console.print(table)
        console.print(f"[dim]Showing jobs scored above {MIN_SCORE_TO_SHOW}/10. Enter a number to analyze or 'q' to quit.[/]\n")
        
        choice = Prompt.ask("Select a job #", default="q")
        if choice.lower() == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(high_potential)):
                raise ValueError
        except ValueError:
            console.print("[red]Invalid selection.[/]")
            continue

        selected_job = high_potential[idx]
        
        # Display Analysis
        console.print(f"\n[bold blue]Deep Analysis: {selected_job['title']} at {selected_job['company']}...[/]")
        
        # Use existing analysis if available
        analysis = None
        if selected_job.get("score_json"):
            try:
                import json
                analysis = json.loads(selected_job["score_json"])
            except: pass
        
        if not analysis:
            analysis = score_job(selected_job["description"])
            update_score_result(selected_job["id"], analysis)
        
        # UI for analysis results
        analysis_grid = Table.grid(expand=True)
        analysis_grid.add_column(style="bold cyan", width=18)
        analysis_grid.add_column()

        score = analysis.get('score', 0)
        grade = analysis.get('grade', 'N/A')
        score_color = "green" if score >= 8 else "yellow" if score >= 6 else "red"
        grade_color = "bold green" if grade == "A" else "green" if grade == "B" else "yellow" if grade == "C" else "red"
        
        analysis_grid.add_row("Match Score", f"[{score_color}]{score}/10[/] ([{grade_color}]{grade}[/])")
        analysis_grid.add_row("Verdict", f"[italic]{analysis.get('verdict', 'N/A')}[/]")
        analysis_grid.add_row("Top Project", f"[bold magenta]{analysis.get('top_project', 'N/A')}[/]")
        
        effort = analysis.get('effort_to_apply', 'medium')
        effort_color = "green" if effort == "low" else "yellow" if effort == "medium" else "red"
        analysis_grid.add_row("Effort to Apply", f"[{effort_color}]{effort.upper()}[/]")
        
        reasons_text = Text()
        for r in analysis.get('match_reasons', []):
            reasons_text.append(f"✅ {r}\n", style="green")
        analysis_grid.add_row("Strengths", reasons_text)

        gaps_text = Text()
        for g in analysis.get('gaps', []):
            gaps_text.append(f"⚠️ {g}\n", style="yellow")
        analysis_grid.add_row("Gaps/Risks", gaps_text)

        console.print(Panel(analysis_grid, title=f" {selected_job['company']} - AI Review ", border_style="blue"))

        # User Decision Point
        action = Prompt.ask(
            "What would you like to do?",
            choices=["1", "2", "3", "q"],
            default="2"
        )

        if action == "1":
            webbrowser.open(selected_job["url"])
            continue
        elif action == "2":
            company = selected_job["company"]
            role = selected_job["title"]
            
            console.print("\n[bold magenta]Step 1:[/] Tailoring resume with Gemini (Jake's Template format)...")
            tailored_md = tailor_resume(selected_job["description"], company, role)
            
            if not tailored_md:
                console.print("[bold red]Error:[/] Could not tailor resume. Check API key.")
                continue

            console.print("[bold magenta]Step 2:[/] Converting to premium PDF...")
            pdf_path = generate_pdf(tailored_md, company, role)
            
            if pdf_path:
                console.print(f"\n[bold green]Success![/] Your tailored resume is ready: [underline cyan]{pdf_path}[/]")
                
                # Auto-open output folder
                try:
                    if sys.platform == "win32": os.system(f"explorer /select,\"{os.path.abspath(pdf_path)}\"")
                    elif sys.platform == "darwin": os.system(f"open -R \"{pdf_path}\"")
                except: pass

                # Logging
                if is_configured():
                    if Confirm.ask("Log this application to Google Sheets?", default=True):
                        log_application(selected_job, analysis, pdf_path)
                
                update_status(selected_job["id"], "applied")
                console.print(f"[SUCCESS] Marked as 'Applied' in local database.")
            else:
                console.print("[bold red]Error:[/] PDF generation failed.")
        elif action == "3" or action == "q":
            continue
def cmd_apply_workflow(job):
    """
    Executes the full application workflow: Tailoring, PDF generation, and Outreach.
    """
    role = job["title"]
    company = job["company"]
    job_id = job["id"]
    pdf_path = ""
    report_path = ""
    sincerely_path = ""

    # STEP 1: Tailor Resume
    console.print("\n[bold]STEP 1/3: Tailoring Resume[/]")
    console.print(f"Tailoring your CV for [bold]{role}[/] at [bold]{company}[/]...")
    
    with console.status("[bold blue]Gemini is rewriting your resume...[/]"):
        tailored_md = tailor_resume(job["description"], company, role)
    
    if not tailored_md:
        console.print("[red][ERROR] Resume tailoring failed.[/]")
        return

    console.print("[green](v) Resume tailored[/]")
    if Confirm.ask("Preview tailored resume?"):
        from rich.markdown import Markdown
        preview_text = tailored_md[:1500] + "\n\n... (content truncated) ..."
        console.print(Panel(Markdown(preview_text), title="Resume Preview"))

    # STEP 2: Generate PDF
    console.print("\n[bold]STEP 2/3: Generating PDF (Jake's Resume Style)[/]")
    if Confirm.ask(f"Generate Jake's Resume PDF for {company}?"):
        from pdf.jake_template import generate_jake_pdf
        pdf_path = generate_jake_pdf(tailored_md, company, role)
        if pdf_path:
            console.print(f"[green](v) PDF ready: {pdf_path}[/]")
            # Open the output folder
            import platform
            try:
                if platform.system() == "Darwin": os.system(f"open output/")
                elif platform.system() == "Linux": os.system(f"xdg-open output/")
                else: os.system(f"explorer output\\")
            except: pass

    # STEP 3: Outreach Research
    console.print("\n[bold]STEP 3/3: Outreach Research[/]")
    if Confirm.ask(f"Run outreach research for {company}?"):
        from scorer.research import run_outreach_research, save_outreach_report
        from rich.markdown import Markdown
        with console.status("[bold blue]Generating outreach package...[/]"):
            outreach = run_outreach_research(company, role)
        
        if outreach:
            console.print(Panel(Markdown(outreach), title=f"Outreach Guide: {company}"))
            report_path = save_outreach_report(outreach, company, role)
            console.print(f"[green](v) Outreach research saved: {report_path}[/]")
            
            # New: Extract copy-paste ready templates for Sincerely extension
            from scorer.research import extract_sincerely_templates
            sincerely_path = extract_sincerely_templates(outreach, company, role)
            console.print(f"[green](v) Sincerely templates exported: {sincerely_path}[/]")

    # STEP 4: Log everything
    update_status(job_id, "applied")
    
    # Get score result for logging
    import json
    score_result = json.loads(job["score_json"]) if job.get("score_json") else {"score": job.get("score", 0)}
    
    if is_configured():
        success = log_application(job, score_result, pdf_path)
        if success:
            console.print("[green](v) Logged to Google Sheets[/]")
        else:
            console.print("[yellow][WARNING] Google Sheets logging failed - check your sheet permissions[/]")
    else:
        console.print("[yellow]Google Sheets not configured. Run 'python main.py sheets_setup' to see instructions.[/]")
    
    # Manual Application Step
    import webbrowser
    console.print("\n[bold yellow]Ready to apply manually.[/]")
    console.print(f"Job URL: [blue underline]{job['url']}[/]")

    if Confirm.ask("Open job posting in browser now?"):
        webbrowser.open(job["url"])
        console.print("[green]✓ Opened in browser. Apply using your tailored PDF from output/[/]")
        console.print(f"[dim]PDF location: {pdf_path}[/]")

    summary_text = f"""
✓ Resume tailored for [bold]{role}[/] at [bold]{company}[/]
✓ PDF: [cyan]{pdf_path if pdf_path else 'Skipped'}[/]
✓ Outreach research: [cyan]{report_path if report_path else 'Skipped'}[/]
✓ Sincerely templates: [cyan]{sincerely_path if report_path else 'Skipped'}[/]

[bold cyan]Next steps:[/]
1. Review the PDF in the [bold]output/[/] folder
2. Apply at: [link={job['url']}]{job['url']}[/link]
3. Use the Copy-Paste templates in [bold]{sincerely_path}[/]
4. Send messages ONE AT A TIME after personalizing [FIRSTNAME]
"""
    console.print(Panel(summary_text, title="Application Package Ready", border_style="green"))

def cmd_apply():
    """
    CLI wrapper for cmd_apply_workflow.
    Usage: python main.py apply {job_id}
    """
    if len(sys.argv) < 3:
        console.print("[red]Usage: python main.py apply {job_id}[/]")
        return
    
    job_id = sys.argv[2]
    job = get_job_by_id(job_id)
    
    if not job:
        console.print(f"[red]Error: Job with ID '{job_id}' not found in database.[/]")
        return
    
    cmd_apply_workflow(job)

def cmd_pipeline(jobs_list: list = None, min_score: float = None):
    """
    Shows all scored jobs ranked by score.
    """
    import json
    if min_score is None:
        try:
            min_score = float(sys.argv[2]) if len(sys.argv) > 2 else MIN_SCORE_TO_SHOW
        except ValueError:
            min_score = MIN_SCORE_TO_SHOW
            
    job_ids = [j["id"] for j in jobs_list] if jobs_list is not None else None
    
    while True:
        if job_ids is not None:
            # Refresh from DB
            all_db_jobs = get_all_jobs()
            jobs = [j for j in all_db_jobs if j["id"] in job_ids and (j.get("score") or 0) >= min_score]
            # Sort by score descending
            jobs.sort(key=lambda x: x.get("score") if x.get("score") is not None else 0, reverse=True)
        else:
            jobs = get_jobs_by_score(min_score)
        
        if not jobs:
            console.print(f"\n[bold yellow]No jobs found with score >= {min_score}.[/]")
            console.print("Try running [cyan]'python main.py scan'[/] to find and score more roles.")
            return

        table = Table(title=f"Ranked Job Pipeline (Score >= {min_score})", box=None, header_style="bold blue")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Grade", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Company", style="bold")
        table.add_column("Role", style="white")
        table.add_column("Location", style="dim")
        table.add_column("Effort", justify="center")
        table.add_column("Rec.", justify="center")

        rec_count = 0
        total_score = 0
        
        for i, job in enumerate(jobs, 1):
            analysis = {}
            if job.get("score_json"):
                try: analysis = json.loads(job["score_json"])
                except: pass
            
            grade = analysis.get("grade", "N/A")
            score = job.get("score") if job.get("score") is not None else 0
            total_score += score
            
            effort = analysis.get("effort_to_apply", "medium")
            rec = "✓" if analysis.get("recommend_apply") else "✗"
            if analysis.get("recommend_apply"): rec_count += 1
            
            # Row coloring based on grade
            row_style = "green" if grade == "A" else "bright_green" if grade == "B" else "yellow" if grade == "C" else "red" if grade == "D" else "dim"
            
            table.add_row(
                str(i),
                grade,
                f"{score}/10",
                job["company"],
                job["title"],
                (job["location"] or "Remote")[:20],
                effort.upper(),
                rec,
                style=row_style
            )

        console.print(table)
        
        avg = total_score / len(jobs) if jobs else 0
        console.print(f"\n[dim]Showing {len(jobs)} jobs | Avg score: {avg:.1f} | Recommended: {rec_count}[/]")
        
        choice = Prompt.ask("\nEnter [bold]job #[/] for full details, or [bold]q[/] to quit", default="q")
        
        if choice.lower() == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(jobs)):
                raise ValueError
            
            selected = jobs[idx]
            analysis = json.loads(selected["score_json"]) if selected.get("score_json") else {}
            
            # Detailed Panel
            detail_grid = Table.grid(expand=True)
            detail_grid.add_column(style="bold cyan", width=20)
            detail_grid.add_column()
            
            detail_grid.add_row("Verdict", f"[italic]{analysis.get('verdict', 'N/A')}[/]")
            
            reasons = analysis.get("match_reasons", [])
            reasons_text = Text()
            for r in reasons: reasons_text.append(f"✓ {r}\n", style="green")
            detail_grid.add_row("Why you match", reasons_text)
            
            gaps = analysis.get("gaps", [])
            gaps_text = Text()
            for g in gaps: gaps_text.append(f"✗ {g}\n", style="red")
            detail_grid.add_row("Gaps", gaps_text)
            
            detail_grid.add_row("Best Project", f"[bold magenta]{analysis.get('top_project', 'N/A')}[/]")
            detail_grid.add_row("URL", f"[link={selected['url']}]{selected['url']}[/link]")
            
            console.print(Panel(
                detail_grid, 
                title=f" {selected['title']} at {selected['company']} — Grade {analysis.get('grade')} ({selected['score']}/10) ",
                border_style="blue"
            ))
            
            # Action Menu
            action = Prompt.ask(
                "\n[bold]Actions[/]: [1] Apply [2] Skip [3] Archive [4] Back",
                choices=["1", "2", "3", "4"],
                default="4"
            )
            
            if action == "1":
                cmd_apply_workflow(selected)
            elif action == "2":
                update_status(selected["id"], "skipped")
                console.print("[yellow]Job skipped.[/]")
            elif action == "3":
                update_status(selected["id"], "archived")
                console.print("[dim]Job archived.[/]")
            # action 4 just loops back
            
        except ValueError:
            console.print("[red]Invalid selection.[/]")
            continue

def cmd_status():
    """
    Shows a summary of application activity.
    """
    all_jobs = get_all_jobs()
    
    stats = {}
    for j in all_jobs:
        status = j.get("status", "new")
        stats[status] = stats.get(status, 0) + 1
        
    status_line = " | ".join([f"[bold]{k}[/]: {v}" for k, v in stats.items()])
    console.print(Panel(status_line, title="Pipeline Status", expand=False))
    
    applied_jobs = get_jobs_by_status("applied")
    if applied_jobs:
        table = Table(title="Applied Jobs History")
        table.add_column("Date", style="dim")
        table.add_column("Company", style="bold")
        table.add_column("Role")
        
        for j in applied_jobs:
            table.add_row(j["created_at"][:10], j["company"], j["title"])
        
        console.print(table)
    else:
        console.print("No applications logged yet.")

def cmd_outreach_research():
    # Parse company and role from sys.argv
    # User runs: python main.py outreach_research "Razorpay Backend Engineer Intern"
    # or:        python main.py outreach_research "Razorpay" "Backend Engineer Intern"

    if len(sys.argv) < 3:
        console.print("[red]Usage: python main.py outreach_research \"Company Role\"[/]")
        console.print("[yellow]Example: python main.py outreach_research \"Razorpay Backend Engineer Intern\"[/]")
        return

    # Join all args after "outreach_research" as the full input
    full_input = " ".join(sys.argv[2:])

    # Try to split company and role: first word = company, rest = role
    # If only one word given, use it as company and prompt for role
    parts = full_input.split(" ", 1)
    if len(parts) == 2:
        company = parts[0]
        role = parts[1]
    else:
        company = parts[0]
        role = Prompt.ask("Enter the target role")

    console.print(f"\n[bold blue]Generating outreach research for:[/]")
    console.print(f"  Company: [bold]{company}[/]")
    console.print(f"  Role: [bold]{role}[/]\n")

    with console.status("Calling Gemini... (this takes 10-20 seconds)"):
        result = run_outreach_research(company, role)

    # Display with rich Markdown
    from rich.markdown import Markdown
    console.print(Markdown(result))

    # Ask to save
    if Confirm.ask("\nSave this research to reports/ folder?"):
        path = save_outreach_report(result, company, role)
        console.print(f"[green]Saved to: {path}[/]")

def show_help():
    # Get Stats for Help Text
    all_jobs = get_all_jobs()
    total = len(all_jobs)
    applied = len([j for j in all_jobs if j.get("status") == "applied"])
    pending = len([j for j in all_jobs if j.get("status") == "new"])

    help_text = Text.from_markup(
        f"Jobs tracked: [bold blue]{total}[/] | Applied: [bold green]{applied}[/] | Pending review: [bold yellow]{pending}[/]\n\n"
        "Usage: [bold cyan]python main.py <command> [args][/]\n\n"
        "[bold cyan]FIND JOBS[/]\n"
        "  scan [dept] [level] [location] [yc]    Scan job portals\n"
        "  internships [india|remote]             YC internships only\n"
        "  pipeline [min_score]                   View ranked matches\n\n"
        "[bold green]APPLY[/]\n"
        "  apply {job_id}                         Full apply workflow\n"
        "  outreach \"Company Role\"                Outreach research\n\n"
        "[bold yellow]TRACK[/]\n"
        "  status                                 Pipeline stats\n"
        "  sheets_setup                           Sheets setup guide\n\n"
        "[bold dim]EXAMPLES[/]\n"
        "  python main.py scan engineering fresher yc\n"
        "  python main.py scan engineering intern india\n"
        "  python main.py internships remote\n"
        "  python main.py pipeline 7\n"
        "  python main.py apply 3"
    )
    console.print(Panel(help_text, title="JobHunt CLI", expand=False))

def main():
    import difflib
    # Database always initialized
    init_db()
    
    # Check config
    try:
        validate_config()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/] {e}")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()
    
    if command in ["help", "--help", "-h"]:
        show_help()
        return

    try:
        if command == "scan":
            cmd_scan()
        elif command == "internships":
            cmd_internships()
        elif command == "pipeline":
            cmd_pipeline()
        elif command == "review":
            department = sys.argv[2].lower() if len(sys.argv) > 2 else None
            cmd_review(department=department)
        elif command == "apply":
            cmd_apply()
        elif command in ["outreach", "outreach_research"]:
            cmd_outreach_research()
        elif command == "status":
            cmd_status()
        elif command == "sheets_setup":
            print_setup_instructions()
        elif command == "audit":
            console.print("[bold yellow]The 'audit' command (Score your CV against a JD) is a placeholder for future development.[/]")
        elif command == "track":
            console.print("[bold yellow]The 'track' command (View full application tracker) is a placeholder for future development.[/]")
        elif command == "demo":
            console.print("[bold yellow]The 'demo' command (Run demo with sample data) is a placeholder for future development.[/]")
        else:
            # Handle typos gracefully
            valid_commands = ["scan", "internships", "pipeline", "review", "apply", "outreach", "status", "sheets_setup", "audit", "track", "demo", "help"]
            matches = difflib.get_close_matches(command, valid_commands, n=1, cutoff=0.6)
            if matches:
                console.print(f"[bold red]Unknown command '{command}'. Did you mean: {matches[0]}?[/]")
            else:
                console.print(f"[bold red]Unknown command '{command}'.[/]")
            show_help()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/]")
        sys.exit(0)

if __name__ == "__main__":
    main()
