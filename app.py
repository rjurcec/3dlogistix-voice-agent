import os
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv
import requests
import gspread
from google.oauth2 import service_account
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI

# Load env vars
load_dotenv()

app = Flask(__name__)

# Load environment variables
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "google-creds.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "3DLogistiX Calls")

# Initialize Google Sheets if credentials available
worksheet = None
try:
    if all([GOOGLE_CREDS_PATH, GOOGLE_SHEET_NAME]):
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=scope)
        gc = gspread.authorize(creds)
        worksheet = gc.open(GOOGLE_SHEET_NAME).sheet1
except Exception as e:
    print(f"[⚠️ Google Sheets Init Error]: {e}")

# Initialize OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.route('/')
def index():
    return "✅ 3DLogistiX Voice Agent is Running."

@app.route('/voice', methods=['POST'])
def voice():
    name = request.form.get('name')
    linkedin = request.form.get('linkedin')
    pain = request.form.get('pain')

    if not all([name, linkedin, pain]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        # Use recent transcript examples if available
        examples = ""
        if worksheet:
            recent = worksheet.get_all_values()[-20:]
            examples = "\n\n".join(
                f"{row[0]} said: '{row[4]}'" for row in recent if len(row) > 4 and row[4].strip()
            )

        # Build prompt
        prompt = (
            f"Based on these recent customer conversations:\n{examples}\n\n"
            f"You are Alex, a friendly AI sales assistant from 3DLogistiX, calling {name} "
            f"(LinkedIn: {linkedin}). Their pain point is: '{pain}'.\n"
            f"Validate the pain, get them to open up. Show empathy. Share how Wilde Brands solved this via our WMS — "
            f"3D warehouse view, automation, integrations with Shopify, Xero, Starshipit, etc.\n"
            f"Close by offering a demo and mention NetSuite, MYOB, and Magento compatibility."
        )

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        script = response.choices[0].message.content.strip()
        print(f"[🧠 GPT SCRIPT]\n{script}")

        # Generate TTS audio
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

        if tts_response.status_code != 200:
            return jsonify({"error": "TTS failed", "details": tts_response.text}), 500

        # Save generated audio temporarily
        with open("output.mp3", "wb") as f:
            for chunk in tts_response.iter_content(chunk_size=4096):
                f.write(chunk)

        # Serve TwiML with audio
        twiml = VoiceResponse()
        twiml.play("https://threedlogistix-voice-agent.onrender.com/static/output.mp3")

        return Response(str(twiml), mimetype='text/xml')

    except Exception as e:
        print(f"[ERROR]: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/twilio/handle-recording', methods=['POST'])
def handle_recording():
    try:
        from_number = request.form.get("From", "")
        to_number = request.form.get("To", "")
        recording_url = request.form.get("RecordingUrl", "")
        call_sid = request.form.get("CallSid", "")
        transcript = request.form.get("TranscriptionText", "")

        if worksheet:
            worksheet.append_row([from_number, to_number, recording_url, call_sid, transcript])
            print(f"[✅ Transcript Saved] Call SID: {call_sid}")
        else:
            print("[⚠️ Worksheet not initialized — skipping logging]")

        return Response("<Response></Response>", mimetype='text/xml')

    except Exception as e:
        print(f"[ERROR - Transcription Save]: {e}")
        return Response("<Response></Response>", mimetype='text/xml', status=200)

@app.route('/analyze-transcripts')
def analyze_transcripts():
    try:
        if not worksheet:
            return jsonify({"error": "Google Sheet not available."}), 503

        rows = worksheet.get_all_values()[-20:]
        transcripts = [row for row in rows if len(row) > 4 and row[4].strip()]

        results = []
        for row in transcripts:
            name, transcript = row[0], row[4]
            prompt = (
                f"Analyze this transcript between Alex and {name}:\n\n{transcript}\n\n"
                "Return JSON with:\n"
                "1. Engagement level\n"
                "2. Sales intent score (1–10)\n"
                "3. Agent tone\n"
                "4. Suggestions to improve"
            )

            try:
                res = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                results.append({"name": name, "analysis": res.choices[0].message.content.strip()})
            except Exception as inner_err:
                results.append({"name": name, "error": str(inner_err)})

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method Not Allowed. Use POST for this endpoint."}), 405

if __name__ == '__main__':
    app.run(debug=False, port=10000, host='0.0.0.0')
















