import os
import uuid
import tempfile
import requests
from flask import Flask, request, Response, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from twilio.twiml.voice_response import VoiceResponse

load_dotenv()
app = Flask(__name__)

# Init OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")


@app.route('/voice')
def voice():
    name = request.args.get('name')
    linkedin = request.args.get('linkedin')
    pain = request.args.get('pain')

    if not all([name, linkedin, pain]):
        return jsonify({"error": "Missing query parameters"}), 400

    print(f"[INFO] Generating voice script for {name}...")

    try:
        prompt = (
            f"You are Alex, a friendly and knowledgeable AI sales assistant from 3DLogistix, calling {name}, "
            f"a warehouse manager. You've seen their LinkedIn profile at {linkedin} and know their key pain point is: '{pain}'. "
            f"Start by validating their potential pain point. Get them to speak about their pain points and show empathy. "
            f"Then explain how companies like Wilde Brands solved similar challenges using the 3DLogistix WMS solution. "
            f"Wilde Brands connects Shopify, Xero, and Starshipit through our platform to automate order flow, stock visibility, "
            f"and managing their warehouse through the 3D view — saving time, seeing where everyone is in the warehouse and reducing human errors. "
            f"Wrap up by offering to book a short call or demo, and mention we also have connectors to other systems like NetSuite, MOYB, and Magento."
        )

        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        script = completion.choices[0].message.content.strip()
        print(f"[INFO] GPT Script: {script}")

        # Stream audio from ElevenLabs
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
            return jsonify({"error": "TTS failed", "details": tts_response.text}), 500

        return Response(
            tts_response.iter_content(chunk_size=4096),
            content_type="audio/mpeg"
        )

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/twilio/voice", methods=["POST"])
def twilio_voice():
    response = VoiceResponse()
    response.say("Hi, this is Alex from 3DLogistix calling about warehouse automation.")
    response.pause(length=1)
    response.say("Please tell me about the challenges you're facing in your warehouse.")
    response.record(
        timeout=5,
        max_length=30,
        transcribe=True,
        action="/twilio/handle-recording",
        play_beep=True
    )
    return str(response)


@app.route("/twilio/handle-recording", methods=["POST"])
def twilio_handle_recording():
    recording_url = request.form.get("RecordingUrl")
    transcription = request.form.get("TranscriptionText")

    print(f"[TWILIO] Recording URL: {recording_url}")
    print(f"[TWILIO] Transcription: {transcription}")

    # Optional: Store transcript or trigger learning logic here

    response = VoiceResponse()
    response.say("Thanks for sharing. We'll follow up shortly.")
    return str(response)


@app.route('/')
def index():
    return "Voice agent is up and running!"


if __name__ == '__main__':
    app.run(debug=False, port=10000, host="0.0.0.0")







