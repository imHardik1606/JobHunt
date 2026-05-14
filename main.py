import sys
import os
import webbrowser
import time
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress

# Project Imports
from scanner import scan_all
from scorer.match import score_job
from tailor.resume import tailor_resume, save_tailored_cv
from pdf.generator import generate_pdf
from tracker.sheets import log_application, is_sheets_configured
from db.store import (
    init_db, save_jobs, get_new_jobs, update_status, 
    update_score, get_unscored_jobs, get_jobs_by_status, get_all_jobs
)
from config import MIN_SCORE_TO_SHOW, validate_config
from scorer.research import run_outreach_research, save_outreach_report

console = Console()

def cmd_scan():
    """
    Scans portals for new jobs and scores them using AI.
    """
    console.print(Panel("[bold blue]Scanning job portals...[/]", expand=False))
    
    jobs = scan_all()
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
    from config import ROLE_KEYWORDS, NEGATIVE_KEYWORDS
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
        if any(kw.lower() in title_lower for kw in ROLE_KEYWORDS):
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
        
    console.print(f"[bold blue]Scoring {len(to_score)} relevant roles with Gemini...[/]")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Scoring jobs...", total=len(to_score))
        
        for job in to_score:
            title = job["title"]
            company = job["company"]
            desc = job.get("description", "")
            
            progress.update(task, description=f"[cyan]Scoring: [bold]{title}[/] at {company}")
            
            result = score_job(desc)
            score = result.get("score", 0)
            
            update_score(job["id"], score)
            progress.advance(task)
            
            # Simple rate limit to stay within Gemini free tier quotas
            time.sleep(2)
        
    console.print("\n[bold green]Scan complete![/] Run [cyan]'python main.py review'[/] to see high-potential leads.")

def cmd_review():
    """
    Interactive review of high-scoring job leads.
    """
    while True:
        all_new = get_new_jobs()
        # Filter by minimum score
        high_potential = [j for j in all_new if (j.get("score") or 0) >= MIN_SCORE_TO_SHOW and j.get("status") == "new"]
        
        if not high_potential:
            console.print(f"\n[bold yellow]No pending high-potential jobs found (Score >= {MIN_SCORE_TO_SHOW}).[/]")
            console.print("Try running [cyan]'python main.py scan'[/] to find more roles.")
            return

        # Sort by score descending
        high_potential.sort(key=lambda x: x.get("score", 0), reverse=True)

        table = Table(title="JobHunt Opportunity Dashboard", box=None, header_style="bold blue")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Match", justify="center")
        table.add_column("Company", style="bold")
        table.add_column("Role", style="white")
        table.add_column("Portal", style="dim")

        for i, job in enumerate(high_potential, 1):
            score = job.get("score", 0)
            score_style = "green" if score >= 8 else "yellow" if score >= 6 else "red"
            
            table.add_row(
                str(i),
                f"[{score_style}]{score*10:.0f}%[/]",
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
        analysis = score_job(selected_job["description"])
        
        # UI for analysis results
        analysis_grid = Table.grid(expand=True)
        analysis_grid.add_column(style="bold cyan", width=15)
        analysis_grid.add_column()

        score = analysis.get('score', 0)
        score_color = "green" if score >= 8 else "yellow" if score >= 6 else "red"
        
        analysis_grid.add_row("Match Score", f"[{score_color}]{score}/10[/]")
        analysis_grid.add_row("Verdict", f"[italic]{analysis.get('verdict', 'N/A')}[/]")
        
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
                if is_sheets_configured():
                    if Confirm.ask("Log this application to Google Sheets?", default=True):
                        log_application(selected_job, analysis, pdf_path)
                
                update_status(selected_job["id"], "applied")
                console.print(f"✅ Marked as 'Applied' in local database.")
            else:
                console.print("[bold red]Error:[/] PDF generation failed.")
        elif action == "3" or action == "q":
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

def cmd_outreach(company: str, role: str):
    """
    Generates a deep outreach research package for a specific company and role.
    """
    console.print(Panel(f"[bold magenta]Starting Outreach Research Assistant Mode[/]\n[cyan]Target:[/] {role} at {company}", expand=False))
    
    with Progress() as progress:
        task = progress.add_task("[magenta]Researching with Gemini...", total=None)
        report_content = run_outreach_research(company, role)
    
    if "failed" in report_content.lower() or "error" in report_content.lower():
        console.print(f"\n[bold red]Error:[/] {report_content}")
        return

    # Display a preview of the research
    console.print(Panel(report_content[:500] + "...", title="Research Preview", border_style="magenta"))
    
    # Save to report
    report_path = save_outreach_report(report_content, company, role)
    if report_path:
        console.print(f"\n[bold green]Success![/] Outreach package saved to: [underline cyan]{report_path}[/]")
        
        if Confirm.ask("Open the report now?", default=True):
            webbrowser.open(os.path.abspath(report_path))
    else:
        console.print("[bold red]Error saving report.[/]")

def main():
    # Database always initialized
    init_db()
    
    # Check config
    try:
        validate_config()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/] {e}")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        # Get Stats for Help Text
        all_jobs = get_all_jobs()
        total = len(all_jobs)
        applied = len([j for j in all_jobs if j.get("status") == "applied"])
        pending = len([j for j in all_jobs if j.get("status") == "new"])

        help_text = Text.from_markup(
            f"Jobs tracked: [bold blue]{total}[/] | Applied: [bold green]{applied}[/] | Pending review: [bold yellow]{pending}[/]\n\n"
            "Usage: [bold cyan]python main.py <command>[/]\n\n"
            "Commands:\n"
            "  [bold green]scan[/]              Fetch new jobs and score them with AI\n"
            "  [bold green]review[/]            Browse high-scoring jobs and generate resumes\n"
            "  [bold green]outreach_research[/]  Generate 5-section outreach package for a target role\n"
            "  [bold green]status[/]            Show application pipeline statistics"
        )
        console.print(Panel(help_text, title="JobHunt CLI", expand=False))
        return

    command = sys.argv[1].lower()
    
    try:
        if command == "scan":
            cmd_scan()
        elif command == "review":
            cmd_review()
        elif command == "status":
            cmd_status()
        elif command == "outreach_research":
            if len(sys.argv) < 4:
                console.print("[bold red]Usage:[/] python main.py outreach_research \"Company\" \"Role\"")
            else:
                cmd_outreach(sys.argv[2], sys.argv[3])
        else:
            console.print(f"[red]Unknown command: {command}[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/]")
        sys.exit(0)

if __name__ == "__main__":
    main()
