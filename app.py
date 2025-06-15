import os
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv
import requests
import gspread
from google.oauth2 import service_account
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse

# Load environment variables
load_dotenv()

# Flask app
app = Flask(__name__)

# Environment variables
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "3DLogistiX Calls")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "google-creds.json")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate config
if not all([ELEVEN_API_KEY, VOICE_ID, GOOGLE_CREDS_PATH, OPENAI_API_KEY]):
    raise EnvironmentError("Missing required environment variables in .env file")

# Google Sheets setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=scope)
gc = gspread.authorize(creds)
worksheet = gc.open(GOOGLE_SHEET_NAME).sheet1

# OpenAI setup
openai_client = OpenAI(api_key=OPENAI_API_KEY)


@app.route('/')
def index():
    return "✅ 3DLogistiX AI voice agent is live."


@app.route('/voice', methods=['POST'])
def voice():
    name = request.form.get('name')
    linkedin = request.form.get('linkedin')
    pain = request.form.get('pain')

    if not all([name, linkedin, pain]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        recent_transcripts = worksheet.get_all_values()[-20:]
        examples = "\n\n".join([
            f"{row[0]} said: '{row[4]}'"
            for row in recent_transcripts if len(row) > 4 and row[4].strip()
        ])

        prompt = (
            f"Based on these recent customer conversations:\n{examples}\n\n"
            f"You are Alex, a friendly and knowledgeable AI sales assistant from 3DLogistiX, calling {name}, "
            f"a warehouse manager. You've seen their LinkedIn profile at {linkedin} and know their key pain point is: '{pain}'. "
            f"Start by validating their potential pain point. Get them to speak about their pain points and show empathy. "
            f"Then explain how companies like Wilde Brands solved similar challenges using the 3DLogistiX WMS solution. "
            f"Wilde Brands connects Shopify, Xero, and Starshipit through our platform to automate order flow, stock visibility, "
            f"and managing their warehouse through the 3D view — saving time, seeing where everyone is in the warehouse and reducing human errors. "
            f"Wrap up by offering to book a short call or demo, and mention we also have connectors to other systems like NetSuite, MYOB, and Magento."
        )

        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        script = completion.choices[0].message.content.strip()

        print(f"[GPT SCRIPT]: {script}")

        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVEN_API_KEY,
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

        if tts_response.status_code != 200:
            return jsonify({"error": "TTS generation failed", "details": tts_response.text}), 500

        return Response(tts_response.iter_content(chunk_size=4096), content_type="audio/mpeg")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/twilio/handle-recording', methods=['POST'])
def handle_recording():
    try:
        from_number = request.form.get("From", "")
        to_number = request.form.get("To", "")
        recording_url = request.form.get("RecordingUrl", "")
        call_sid = request.form.get("CallSid", "")
        transcript = request.form.get("TranscriptionText", "")

        worksheet.append_row([
            from_number,
            to_number,
            recording_url,
            call_sid,
            transcript
        ])
        print(f"[INFO] Saved recording & transcript for Call SID: {call_sid}")

        return Response("<Response></Response>", mimetype='text/xml')

    except Exception as e:
        print(f"[ERROR - Recording fallback] {e}")
        return Response("<Response></Response>", mimetype='text/xml', status=200)


@app.route('/analyze-transcripts')
def analyze_transcripts():
    try:
        rows = worksheet.get_all_values()[-20:]
        transcripts = [row for row in rows if len(row) > 4 and row[4].strip()]

        results = []
        for row in transcripts:
            name = row[0]
            transcript = row[4]
            prompt = (
                f"Analyze this customer transcript between Alex (AI agent) and {name}:\n\n{transcript}\n\n"
                "Evaluate:\n"
                "1. Engagement (low/med/high)\n"
                "2. Sales intent score (1–10)\n"
                "3. Agent tone (positive, neutral, robotic, aggressive)\n"
                "4. Suggestions for tone/pacing/conversion\n\nReturn as JSON."
            )

            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                analysis = completion.choices[0].message.content.strip()
                results.append({"name": name, "analysis": analysis})
            except Exception as gpt_err:
                results.append({"name": name, "error": str(gpt_err)})

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Catch-all for unsupported methods
@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method Not Allowed. Use POST for this endpoint."}), 405


if __name__ == '__main__':
    app.run(debug=False, port=10000, host="0.0.0.0")















