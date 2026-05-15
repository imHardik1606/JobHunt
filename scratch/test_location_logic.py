import sys
import os
# Add parent directory to path to import scanner
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import scan_all, Job
from unittest.mock import patch, MagicMock

def test_location_filtering():
    mock_jobs = [
        Job(id="1", title="Engineer", company="A", location="Bangalore, India", url="http://a.com", description="Java", portal="lever"),
        Job(id="2", title="Engineer", company="B", location="Remote", url="http://b.com", description="Java", portal="lever"),
        Job(id="3", title="Engineer", company="C", location="San Francisco, USA", url="http://c.com", description="Java", portal="lever"),
        Job(id="4", title="Engineer", company="D", location="Anywhere", url="http://d.com", description="Java", portal="lever"),
        Job(id="5", title="Engineer", company="E", location="Hyderabad", url="http://e.com", description="Java", portal="lever"),
    ]

    with patch('scanner.COMPANIES', [{"name": "TestCo", "portal": "lever", "id": "test"}]):
        with patch('scanner.PORTAL_FETCHERS', {"lever": lambda name, cid: mock_jobs}):
            with patch('scanner.get_department_keywords', return_value=["Engineer"]):
                
                print("Testing with country='india'...")
                jobs_india = scan_all(department="engineering", country="india")
                titles_india = [j.company for j in jobs_india]
                print(f"Found: {titles_india}")
                # Should find A (India), B (Remote), D (Anywhere)
                assert "A" in titles_india
                assert "B" in titles_india
                assert "D" in titles_india
                assert "C" not in titles_india
                assert "E" not in titles_india
                
                print("\nTesting with country='remote'...")
                jobs_remote = scan_all(department="engineering", country="remote")
                titles_remote = [j.company for j in jobs_remote]
                print(f"Found: {titles_remote}")
                # Should find B (Remote), D (Anywhere)
                assert "B" in titles_remote
                assert "D" in titles_remote
                assert "A" not in titles_remote
                assert "C" not in titles_remote
                assert "E" not in titles_remote

                print("\nTesting with no country...")
                jobs_all = scan_all(department="engineering")
                titles_all = [j.company for j in jobs_all]
                print(f"Found: {titles_all}")
                assert len(titles_all) == 5

                print("\nAll tests passed!")

if __name__ == "__main__":
    try:
        test_location_filtering()
    except AssertionError as e:
        print(f"Test failed!")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
