import os
import uuid
from flask import Flask, request, Response, jsonify, send_from_directory
from dotenv import load_dotenv
import requests
import gspread
from google.oauth2 import service_account
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
STATIC_FOLDER = app.static_folder

# Config
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "google-creds.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "3DLogistiX Calls")

# Initialize OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Google Sheets Setup
worksheet = None
try:
    if GOOGLE_CREDS_PATH and GOOGLE_SHEET_NAME:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        worksheet = gc.open(GOOGLE_SHEET_NAME).sheet1
except Exception as e:
    print(f"[⚠️ Google Sheets Init Error]: {e}")

@app.route("/voice", methods=["GET", "POST"])
def voice():
    try:
        name = request.values.get("name", "there")
        linkedin = request.values.get("linkedin", "")
        pain = request.values.get("pain", "some operational challenges")

        if not name or not pain:
            return jsonify({"error": "Missing parameters"}), 400

        # Pull recent examples if available
        examples = ""
        if worksheet:
            recent = worksheet.get_all_values()[-20:]
            examples = "\n\n".join(
                f"{row[0]} said: '{row[4]}'"
                for row in recent if len(row) > 4 and row[4].strip()
            )

        # Build prompt
        prompt = (
            f"Based on these recent customer conversations:\n{examples}\n\n"
            f"You are Alex, a friendly AI sales assistant from 3DLogistiX, calling {name} "
            f"(LinkedIn: {linkedin}). Their pain point is: '{pain}'.\n"
            f"Validate the pain, show empathy, and explain how Wilde Brands solved this via our WMS — "
            f"3D warehouse view, automation, integrations with Shopify, Xero, Starshipit, etc.\n"
            f"Offer a demo and mention NetSuite, MYOB, and Magento compatibility."
        )

        # Generate script
        script = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content.strip()

        # Generate audio
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(STATIC_FOLDER, audio_filename)

        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVEN_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": script,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            stream=True
        )

        if tts_response.status_code == 200:
            with open(audio_path, "wb") as f:
                for chunk in tts_response.iter_content(chunk_size=4096):
                    f.write(chunk)
        else:
            print(f"[⚠️ TTS Error]: {tts_response.text}")
            audio_filename = "sample.mp3"
            audio_path = os.path.join(STATIC_FOLDER, audio_filename)
            if not os.path.exists(audio_path):
                return jsonify({"error": "sample.mp3 missing for fallback"}), 500

        # Twilio voice response
        response = VoiceResponse()
        response.play(f"https://threedlogistix-voice-agent.onrender.com/static/{audio_filename}")
        return Response(str(response), mimetype='text/xml')

    except Exception as e:
        print(f"[❌ Error]: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=False, port=10000, host='0.0.0.0')

















