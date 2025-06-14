from flask import Flask, request, send_file, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from openai import OpenAI
import os
import uuid
import requests

load_dotenv()
print("DEBUG: OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "hCjNJSMrJ5BSeizBkC9X")

client = OpenAI(api_key=OPENAI_API_KEY)
conversations = {}

# --- Browser-Based Voice Route ---
@app.route('/voice')
def voice_browser():
    name = request.args.get('name')
    linkedin = request.args.get('linkedin')
    pain = request.args.get('pain')
    print(f"[INFO] Generating voice script for {name}...")

    try:
        script = generate_script(name, linkedin, pain)
        print(f"[INFO] GPT Script: {script}")
        audio_path = text_to_speech(script)
        print(f"[INFO] Audio path: {audio_path}")
        return send_file(audio_path, mimetype="audio/mpeg")
    except Exception as e:
        print(f"[ERROR] Something went wrong: {e}")
        return jsonify({'error': str(e)}), 500

# --- GPT-based script generation ---
def generate_script(name, linkedin, pain):
    prompt = (
        f"You are Alex, an AI sales assistant from 3DLogistiX, calling {name}, a warehouse manager. "
        f"You saw their LinkedIn at {linkedin}. They shared the pain point: '{pain}'. "
        f"Engage them with a helpful tone. Mention Wilde Brands solving similar issues via integrations "
        f"with Shopify, Xero, and Starshipit. Also explain 3DLogistiX has connectors to systems like NetSuite, DEAR, and Unleashed. "
        f"Wrap up by offering a demo or follow-up call."
    )
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content.strip()

# --- ElevenLabs Text-to-Speech ---
def text_to_speech(text):
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream",
        headers=headers,
        json=data
    )
    filename = f"static/{uuid.uuid4()}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

# --- Twilio Voice Route Preserved ---
@app.route("/twilio-voice", methods=["GET", "POST"])
def voice_twilio():
    call_sid = request.values.get("CallSid")
    name = request.args.get("name", "there")
    linkedin = request.args.get("linkedin", "N/A")
    pain = request.args.get("pain", "a warehouse challenge")

    prompt = (
        f"You are Alex, an AI sales assistant from 3DLogistiX, calling {name}, a warehouse manager. "
        f"You saw their LinkedIn at {linkedin}. They shared the pain point: '{pain}'. "
        f"Engage them with a helpful tone. Mention Wilde Brands solving similar issues via integrations "
        f"with Shopify, Xero, and Starshipit. Also explain 3DLogistiX has connectors to systems like NetSuite, DEAR, and Unleashed. "
        f"Wrap up by offering a demo or follow-up call."
    )

    conversations[call_sid] = [{"role": "user", "content": prompt}]

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=conversations[call_sid]
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT error - /twilio-voice] {str(e)}")
        reply = "Hi! This is Alex from 3DLogistiX. I wanted to share how we help with warehouse operations."

    conversations[call_sid].append({"role": "assistant", "content": reply})
    audio_url = generate_audio(reply)

    resp = VoiceResponse()
    if audio_url:
        resp.play(audio_url)
    else:
        resp.say(reply)

    gather = Gather(input="speech", action="/process", method="POST", timeout=6)
    gather.say("Would you like to share how you're managing this today?")
    resp.append(gather)

    return str(resp)

# Optional: Audio URL generator for Twilio (via ElevenLabs)
def generate_audio(text):
    try:
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream",
            headers=headers,
            json=data
        )
        filename = f"static/{uuid.uuid4()}.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)
        return f"{request.url_root}static/{os.path.basename(filename)}"
    except Exception as e:
        print(f"[generate_audio error] {str(e)}")
        return None

@app.route("/")
def index():
    return "3DLogistiX AI Voice Agent is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)







