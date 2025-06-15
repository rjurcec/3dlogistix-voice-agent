import csv
import os
import time
from urllib.parse import urlencode
from twilio.rest import Client
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twilio setup
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)

# Webhook URL of deployed Flask server
BASE_WEBHOOK_URL = os.getenv("WEBHOOK_BASE_URL", "https://threedlogistix-voice-agent.onrender.com")

# Google Sheets setup
creds_path = os.getenv("GOOGLE_CREDS_PATH", "google-creds.json")
sheet_name = os.getenv("GOOGLE_SHEET_NAME", "3DLogistiX Calls")
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

sheet = None
try:
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    gc = gspread.authorize(creds)
    sheet = gc.open(sheet_name).sheet1
except Exception as e:
    print(f"❌ Failed to connect to Google Sheets: {e}")

def retry(func, max_attempts=3, delay=2, backoff=2):
    """
    Generic retry function.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt == max_attempts:
                raise
            time.sleep(delay)
            delay *= backoff

def log_to_sheet(name, phone, pain):
    """
    Logs the outbound call attempt to Google Sheets.
    """
    if not sheet:
        print(f"⚠️ Skipping log to sheet — sheet not initialized.")
        return

    def do_log():
        timestamp = datetime.now().isoformat()
        sheet.append_row([name, phone, pain, "Call placed", timestamp])

    try:
        retry(do_log)
    except Exception as e:
        print(f"❌ Failed to log to sheet for {name}: {e}")

def call_contact(contact):
    """
    Places a call via Twilio to a contact and logs the attempt.
    """
    name = contact.get("name", "").strip()
    phone = contact.get("phone", "").strip()
    linkedin = contact.get("linkedin", "").strip()
    pain = contact.get("pain_point", "").strip()

    if not all([name, phone, linkedin, pain]):
        print(f"⚠️ Skipping contact due to missing fields: {contact}")
        return

    query_params = urlencode({
        "name": name,
        "linkedin": linkedin,
        "pain": pain
    })

    def do_call():
        return client.calls.create(
            to=phone,
            from_=twilio_number,
            url=f"{BASE_WEBHOOK_URL}/voice?{query_params}"
        )

    try:
        call = retry(do_call)
        print(f"✅ Call placed to {name} ({phone}) | Call SID: {call.sid}")
        log_to_sheet(name, phone, pain)
    except Exception as e:
        print(f"❌ Error calling {name} ({phone}): {str(e)}")

def load_contacts_and_call(csv_path="contacts.csv"):
    """
    Reads a CSV of contacts and places outbound calls to each.
    """
    try:
        with open(csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                call_contact(row)
    except FileNotFoundError:
        print(f"❌ CSV file not found at path: {csv_path}")
    except Exception as e:
        print(f"❌ Failed to load contacts: {str(e)}")

if __name__ == "__main__":
    load_contacts_and_call()


