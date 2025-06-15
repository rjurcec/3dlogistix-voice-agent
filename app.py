import os
import uuid
import time
import requests
import traceback
import threading
from urllib.parse import urlencode
from flask import Flask, request, Response, send_from_directory, url_for, jsonify
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
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
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("gspread-service-account.json", scopes=scope)
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

        query_params = {
            "name": name,
            "linkedin": linkedin,
            "pain": pain,
            "file": audio_filename
        }
        final_audio_url = f"{request.url_root}voice-final?{urlencode(query_params)}"

        thread = threading.Thread(target=generate_audio, args=(name, linkedin, pain, audio_path, audio_filename))
        thread.start()

        twiml = VoiceResponse()
        twiml.play(url_for("static", filename="preparing.mp3", _external=True))
        twiml.pause(length=2)
        twiml.redirect(final_audio_url)

        return Response(str(twiml), mimetype="text/xml")

    except Exception:
        print(f"[❌ Error]: {traceback.format_exc()}")
        return Response("<Response><Say>Something went wrong.</Say></Response>", mimetype="text/xml")

@app.route("/voice-final", methods=["GET", "POST"])
def voice_final():
    try:
        filename = request.args.get("file")
        file_path = os.path.join(STATIC_FOLDER, filename)

        twiml = VoiceResponse()

        timeout = 10
        interval = 1
        waited = 0

        while waited < timeout:
            if os.path.exists(file_path):
                twiml.play(url_for("static", filename=filename, _external=True))
                break
            time.sleep(interval)
            waited += interval

        if waited >= timeout:
            twiml.say("We’re sorry, your custom message is still being generated.")
            twiml.pause(length=2)
            twiml.say("Please try again later.")

        return Response(str(twiml), mimetype="text/xml")

    except Exception:
        print(f"[❌ Error]: {traceback.format_exc()}")
        return Response("<Response><Say>Something went wrong.</Say></Response>", mimetype="text/xml")

def generate_audio(name, linkedin, pain, audio_path, audio_filename):
    try:
        examples = ""
        if sheet:
            recent = sheet.get_all_values()[-10:]
            examples = "\n\n".join(f"{row[0]} said: '{row[4]}'" for row in recent if len(row) > 4 and row[4].strip())

        prompt = f"""
You are an outbound sales agent from 3DLogistiX, calling {name} who does not know who we are. 
They are struggling with: \"{pain}\". LinkedIn: {linkedin}

Be helpful and informative. Mention real-time 3D warehouse visualisation, automation, Shopify/Xero/MYOB/Magento integrations, and how Wilde Brands used it.

Recent examples:\n\n{examples}
"""
        print(f"[🧠 GPT Prompt Sent]\n{prompt.strip()}")

        gpt_response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful sales rep."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        script = gpt_response.choices[0].message.content.strip()
        print(f"[✅ GPT-4 Response]\n{script}")

        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        tts_headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        tts_payload = {
            "text": script,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        print(f"[🔊 Sending to ElevenLabs] {tts_url}")
        print(f"[🧪 Saving to path]: {audio_path}")

        tts_response = requests.post(tts_url, headers=tts_headers, json=tts_payload, stream=True)

        if tts_response.ok:
            print(f"[🔊 ElevenLabs TTS Response OK] Writing to: {audio_path}")
            with open(audio_path, "wb") as f:
                for chunk in tts_response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            print(f"[✅ Audio Saved] /static/{audio_filename}")
        else:
            print(f"[❌ ElevenLabs TTS Error] Status Code: {tts_response.status_code}")
            print(f"[❌ ElevenLabs Response]: {tts_response.text}")
            return

        if sheet:
            sheet.append_row([name, linkedin, pain, script, script])

    except Exception:
        print(f"[❌ Background Gen Error]: {traceback.format_exc()}")

@app.route("/debug-static")
def debug_static():
    static_path = os.path.join(app.static_folder)
    files = os.listdir(static_path)
    return jsonify({"static_path": static_path, "files": files})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


