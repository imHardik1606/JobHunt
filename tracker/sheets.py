import os
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_ID

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Applications"

# Color Definitions
COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
COLOR_BLACK_BG = {"red": 0.13, "green": 0.13, "blue": 0.13}
COLOR_GREEN = {"red": 0.13, "green": 0.73, "blue": 0.36}
COLOR_TEAL = {"red": 0.13, "green": 0.60, "blue": 0.67}
COLOR_YELLOW = {"red": 0.98, "green": 0.82, "blue": 0.13}
COLOR_ORANGE = {"red": 0.98, "green": 0.60, "blue": 0.13}
COLOR_RED = {"red": 0.90, "green": 0.22, "blue": 0.22}
COLOR_BLUE = {"red": 0.23, "green": 0.51, "blue": 0.97}

def is_sheets_configured() -> bool:
    """Legacy alias for is_configured."""
    return is_configured()

def is_configured() -> bool:
    """
    Return True only if BOTH service_account.json exists AND GOOGLE_SHEETS_ID is set.
    """
    try:
        return os.path.exists(SERVICE_ACCOUNT_FILE) and bool(GOOGLE_SHEETS_ID)
    except:
        return False

def _get_applications_sheet():
    """
    Authenticates and returns the 'Applications' worksheet.
    Creates it if it doesn't exist and writes the header if new.
    """
    if not is_configured():
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=12)
            
        # Check if empty or needs header
        all_vals = worksheet.get_all_values()
        if not all_vals or (len(all_vals) == 1 and not any(all_vals[0])):
            header = [
                "Applied On", "Company", "Role", "Location", "Score", "Grade",
                "Recommend", "Description", "Job URL", "Status", "Resume PDF", "Notes"
            ]
            worksheet.append_row(header)
            
            # Format header
            worksheet.format("A1:L1", {
                "backgroundColor": COLOR_BLACK_BG,
                "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True, "fontSize": 11},
                "horizontalAlignment": "CENTER"
            })
            
            # Freeze header
            worksheet.freeze(rows=1)
            
            # Set column widths
            widths = [100, 130, 200, 100, 60, 60, 100, 300, 250, 100, 200, 150]
            for i, width in enumerate(widths, 1):
                worksheet.set_column_width(i, width)
            
        return worksheet
    except Exception as e:
        print(f"[ERROR] Google Sheets Connection Error: {e}")
        return None

def log_application(job: dict, score_result: dict, pdf_path: str = "") -> bool:
    """
    Logs a single job application to the Google Sheet.
    Returns True on success, False on any exception.
    """
    try:
        ws = _get_applications_sheet()
        if not ws:
            return False
            
        desc = job.get("description", "")
        truncated_desc = (desc[:300] + "...") if len(desc) > 300 else desc

        score = score_result.get("score", 0)
        grade = score_result.get("grade", "N/A")
        recommend = "Yes" if score_result.get("recommend_apply") else "No"
        
        row = [
            datetime.now().strftime("%d-%m-%Y"),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", "Not specified"),
            score,
            grade,
            recommend,
            truncated_desc,
            job.get("url", ""),
            "Applied",
            pdf_path,
            "" # Notes
        ]
        
        ws.append_row(row)
        
        # Get last row number
        last_row = len(ws.get_all_values())
        
        # Format Score (Column E)
        score_color = COLOR_RED
        if score >= 8: score_color = COLOR_GREEN
        elif score >= 6: score_color = COLOR_TEAL
        elif score >= 5: score_color = COLOR_YELLOW
        
        ws.format(f"E{last_row}", {
            "backgroundColor": score_color,
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        
        # Format Grade (Column F)
        grade_color = COLOR_RED
        if grade == "A": grade_color = COLOR_GREEN
        elif grade == "B": grade_color = COLOR_TEAL
        elif grade == "C": grade_color = COLOR_YELLOW
        elif grade == "D": grade_color = COLOR_ORANGE
        
        ws.format(f"F{last_row}", {
            "backgroundColor": grade_color,
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        
        # Format Recommend (Column G)
        rec_color = COLOR_GREEN if recommend == "Yes" else COLOR_RED
        ws.format(f"G{last_row}", {
            "backgroundColor": rec_color,
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        
        # Format Status (Column J)
        ws.format(f"J{last_row}", {
            "backgroundColor": COLOR_BLUE,
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error logging to Google Sheets: {e}")
        return False

def print_setup_instructions():
    """
    Prints detailed setup instructions for Google Sheets integration.
    """
    print("\n--- Google Sheets Setup Instructions ---")
    print("1. Go to console.cloud.google.com")
    print("2. Create project -> Enable Google Sheets API + Google Drive API")
    print("3. Credentials -> Service Account -> Create -> Download JSON key")
    print("4. Rename downloaded file to service_account.json, place in project root")
    print("5. Create a Google Sheet -> copy the ID from the URL (between /d/ and /edit)")
    print("6. Add GOOGLE_SHEETS_ID=your_id to .env")
    print("7. Open the sheet -> Share with the service account email (Editor access)")
    print("   The email looks like: name@project-id.iam.gserviceaccount.com\n")

def update_application_status(company: str, role: str, new_status: str):
    """
    Finds an application by company and role, then updates its status with color.
    """
    try:
        ws = _get_applications_sheet()
        if not ws: return
        
        all_rows = ws.get_all_values()
        
        for i, row in enumerate(all_rows[1:], start=2):
            # Col B: Company (index 1), Col C: Role (index 2)
            if row[1] == company and row[2] == role:
                # Update Col J (Status) - Column index 9
                ws.update_cell(i, 10, new_status)
                
                # Color status cell
                color = COLOR_BLUE
                if new_status == "Interviewing": color = COLOR_ORANGE
                elif new_status == "Offered": color = COLOR_GREEN
                elif new_status == "Rejected": color = COLOR_RED
                
                ws.format(f"J{i}", {
                    "backgroundColor": color, 
                    "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True},
                    "horizontalAlignment": "CENTER"
                })
                
                print(f"[SUCCESS] Updated {company} - {role} status to: {new_status}")
                return
        
    except Exception as e:
        print(f"[ERROR] Error updating status: {e}")

if __name__ == "__main__":
    if not is_configured():
        print_setup_instructions()
    else:
        print("[SUCCESS] Google Sheets appears to be configured correctly.")
        ws = _get_applications_sheet()
        if ws:
            print(f"[SUCCESS] Successfully connected to sheet: {ws.spreadsheet.title}")
        else:
            print("[ERROR] Configuration exists but connection failed.")
