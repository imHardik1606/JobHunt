import os
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_ID

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Applications"

def is_sheets_configured() -> bool:
    """
    Checks if the minimum requirements for Google Sheets logging are met.
    """
    return os.path.exists(SERVICE_ACCOUNT_FILE) and bool(GOOGLE_SHEETS_ID)

def _get_sheet():
    """
    Authenticates and returns the 'Applications' worksheet.
    Creates it if it doesn't exist.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            "❌ 'service_account.json' not found in project root.\n"
            "Setup Guide: \n"
            "1. Create a project in Google Cloud Console\n"
            "2. Enable Google Sheets and Google Drive APIs\n"
            "3. Create a Service Account and download the JSON key as 'service_account.json'\n"
            "4. Share your Google Sheet with the email in the service_account.json file."
        )

    if not GOOGLE_SHEETS_ID:
        raise ValueError("❌ GOOGLE_SHEETS_ID is not set in your .env file.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Create worksheet if not exists
        worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=12)
        
    # Check if empty (no header)
    if not worksheet.get_all_values():
        header = [
            "Date", "Company", "Role", "Score", "Recommend Apply",
            "Match Reasons", "Gaps", "Verdict", "URL", "Status", "PDF Path", "Notes"
        ]
        worksheet.append_row(header)
        
    return worksheet

def log_application(job: dict, score_result: dict, pdf_path: str = "", notes: str = "") -> bool:
    """
    Logs a single job application to the Google Sheet.
    Includes exact setup steps if configuration is missing.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print("❌ Error: 'service_account.json' is missing.")
        print("💡 Setup Instructions:")
        print("   1. Go to console.cloud.google.com")
        print("   2. Create project → Enable Sheets API + Drive API")
        print("   3. Credentials → Service Account → Create → Download JSON")
        print("   4. Rename to service_account.json and put in project root")
        print("   5. Share your Google Sheet with the service account email")
        return False

    try:
        ws = _get_sheet()
        
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            job.get("company", ""),
            job.get("title", ""),
            score_result.get("score", ""),
            "Yes" if score_result.get("recommend_apply") else "No",
            " | ".join(score_result.get("match_reasons", []) or []),
            " | ".join(score_result.get("gaps", []) or []),
            score_result.get("verdict", ""),
            job.get("url", ""),
            "Applied",
            pdf_path,
            notes
        ]
        
        ws.append_row(row)
        return True
        
    except Exception as e:
        print(f"❌ Error logging to Google Sheets: {e}")
        return False

def update_application_status(company: str, role: str, new_status: str):
    """
    Finds an application by company and role, then updates its status.
    """
    try:
        ws = _get_sheet()
        all_rows = ws.get_all_values()
        
        # Header is at index 0, data starts at index 1
        for i, row in enumerate(all_rows[1:], start=2):
            # Col A: Company, Col B: Role
            if row[1] == company and row[2] == role:
                # Update Col J (Status) - Column index 10
                ws.update_cell(i, 10, new_status)
                print(f"✅ Updated {company} - {role} status to: {new_status}")
                return
        
        print(f"⚠️ Row not found for {company} - {role}")
        
    except Exception as e:
        print(f"❌ Error updating status: {e}")

if __name__ == "__main__":
    if not is_sheets_configured():
        print("--- Google Sheets Setup Required ---")
        print("1. Ensure 'service_account.json' exists in the project root.")
        print("2. Ensure 'GOOGLE_SHEETS_ID' is set in your '.env' file.")
    else:
        print("✅ Google Sheets appears to be configured correctly.")
        try:
            # Attempt to connect to verify
            ws = _get_sheet()
            print(f"✅ Successfully connected to sheet: {ws.spreadsheet.title}")
        except Exception as e:
            print(f"❌ Configuration exists but connection failed: {e}")
