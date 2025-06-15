import os
import uuid
import requests
import traceback
import threading
from flask import Flask, request, Response, send_from_directory, url_for
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")
STATIC_FOLDER = app.static_folder

# ENV VARS
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")

# OpenAI client
openai = OpenAI(api_key=OPENAI_API_KEY)

# Google Sheets setup
sheet = None
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('gspread-service-account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_KEY).sheet1
except Exception as e:
    print(f"[⚠️ Google Sheets Init Error] {e}")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

@app.route("/voice", methods=["GET", "POST"])
def voice():
    try:
        name = request.values.get("name", "there")
        linkedin = request.values.get("linkedin", "")
        pain = request.values.get("pain", "some operational challenges")

        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(STATIC_FOLDER, audio_filename)
        audio_url = url_for('static', filename=audio_filename, _external=True)

        # Replace 'sample.mp3' with your real intro file
        placeholder_filename = "preparing.mp3"
        placeholder_url = url_for('static', filename=placeholder_filename, _external=True)

        # Return TwiML immediately with placeholder
        twiml = VoiceResponse()
        twiml.play(placeholder_url)

        # Start background processing
        thread = threading.Thread(target=generate_audio, args=(name, linkedin, pain, audio_path, audio_filename))
        thread.start()

        return Response(str(twiml), mimetype='text/xml')

    except Exception as e:
        print(f"[❌ Error]: {traceback.format_exc()}")
        return Response("<Response><Say>Something went wrong.</Say></Response>", mimetype='text/xml')

def generate_audio(name, linkedin, pain, audio_path, audio_filename):
    try:
        # Pull examples
        examples = ""
        if sheet:
            recent = sheet.get_all_values()[-10:]
            examples = "\n\n".join(f"{row[0]} said: '{row[4]}'" for row in recent if len(row) > 4 and row[4].strip())

        prompt = f"""
You are an outbound sales agent from 3DLogistiX, calling {name} who does not know who we are. 
They are struggling with: "{pain}". LinkedIn: {linkedin}

Be helpful and informative. Mention real-time 3D warehouse visualisation, automation, Shopify/Xero/MYOB/Magento integrations, and how Wilde Brands used it.

Recent examples:\n\n{examples}
"""

        gpt_response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful sales rep."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        script = gpt_response.choices[0].message.content.strip()

        # Generate audio
        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": script,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            stream=True
        )

        if tts_response.ok:
            with open(audio_path, "wb") as f:
                for chunk in tts_response.iter_content(chunk_size=4096):
                    f.write(chunk)
            print(f"[✅ Audio Generated] Saved to {audio_filename}")
        else:
            print(f"[⚠️ TTS Error]: {tts_response.text}")

        if sheet:
            sheet.append_row([name, linkedin, pain, script, script])

    except Exception as e:
        print(f"[❌ Background Gen Error]: {traceback.format_exc()}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)














