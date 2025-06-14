import csv
import os
from urllib.parse import urlencode
from twilio.rest import Client
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

# ✅ Load environment variables from .env file (local testing)
load_dotenv()

# Twilio credentials from environment
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)

# Deployed Flask app endpoint
BASE_WEBHOOK_URL = "https://threedlogistix-voice-agent.onrender.com"

# Google Sheets setup
creds = Credentials.from_service_account_file("/etc/secrets/google-creds.json")
gc = gspread.authorize(creds)
sheet = gc.open("3DLogistiX Calls").sheet1

def log_to_sheet(name, phone, pain):
    """Log call attempt to Google Sheet with timestamp."""
    sheet.append_row([name, phone, pain, "Call placed", datetime.now().isoformat()])

def build_prompt(name, linkedin, pain):
    """Builds the AI prompt (currently unused; logic moved to Flask endpoint)."""
    return (
        f"You are Alex, a friendly and knowledgeable AI sales assistant from 3DLogistix, calling {name}, "
        f"a warehouse manager. You've seen their LinkedIn profile at {linkedin} and know their key pain point is: '{pain}'. "
        f"Start by validating their potential pain point. Get them to speak about their pain points and show empathy. "
        f"Then explain how companies like Wilde Brands solved similar challenges using the 3DLogistix WMS solution. "
        f"Wilde Brands connects Shopify, Xero, and Starshipit through our platform to automate order flow, stock visibility, "
        f"and managing their warehouse through the 3D view  — saving time, seeing where everyone is in the warehouse and reducing human errors. "
        f"Wrap up by offering to book a short call or demo, and mention we also have connectors to other systems like NetSuite, MOYB, and Magento."
    )

def call_contact(contact):
    """Triggers an outbound call via Twilio and logs it to Google Sheets."""
    name = contact["name"]
    phone = contact["phone"]
    linkedin = contact["linkedin"]
    pain = contact["pain_point"]

    params = urlencode({
        "name": name,
        "linkedin": linkedin,
        "pain": pain
    })

    try:
        call = client.calls.create(
            to=phone,
            from_=twilio_number,
            url=f"{BASE_WEBHOOK_URL}/voice?{params}"
        )
        log_to_sheet(name, phone, pain)
        print(f"✅ Call placed to {name} ({phone}) | SID: {call.sid}")
    except Exception as e:
        print(f"❌ Failed to call {name} ({phone}): {str(e)}")

def load_contacts_and_call(csv_path="contacts.csv"):
    """Loads contacts from CSV and places outbound calls."""
    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            call_contact(row)

if __name__ == "__main__":
    load_contacts_and_call()
