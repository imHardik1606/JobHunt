from scanner import scan_all

if __name__ == "__main__":
    jobs = scan_all()
    print(f"\nTotal relevant jobs found: {len(jobs)}")
    for j in jobs[:5]:
        print(f"- {j.title} @ {j.company} ({j.portal})")
