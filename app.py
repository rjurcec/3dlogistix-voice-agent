from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import requests
import os
import uuid

app = Flask(__name__)

# Load API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "hCjNJSMrJ5BSeizBkC9X")

# In-memory conversation tracking
conversations = {}

# Text-to-speech using ElevenLabs
def generate_audio(text):
    try:
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
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

# Initial call handler
@app.route("/voice", methods=["POST", "GET"])
def voice():
    call_sid = request.values.get('CallSid')
    name = request.args.get("name", "there")
    linkedin = request.args.get("linkedin", "N/A")
    pain = request.args.get("pain", "a warehouse challenge")

    # Build GPT prompt
    prompt = (
        f"You are Alex, an AI sales assistant from 3DLogistiX, calling {name}, a warehouse manager. "
        f"You saw their LinkedIn at {linkedin}. They shared the pain point: '{pain}'. "
        f"Engage them with a helpful tone. Mention Wilde Brands solving similar issues via integrations "
        f"with Shopify, Xero, and Starshipit. Also explain 3DLogistiX has connectors to systems like NetSuite, DEAR, and Unleashed. "
        f"Wrap up by offering a demo or follow-up call."
    )

    # Store conversation state
    conversations[call_sid] = [{"role": "user", "content": prompt}]

    # GPT-4 response
    try:
        reply = openai.ChatCompletion.create(
            model="gpt-4",
            messages=conversations[call_sid]
        )['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[GPT error - /voice] {str(e)}")
        reply = "Hi! This is Alex from 3DLogistiX. I wanted to share how we help with warehouse operations."

    conversations[call_sid].append({"role": "assistant", "content": reply})

    # Voice response
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

# Continue conversation based on user speech
@app.route("/process", methods=["POST"])
def process():
    call_sid = request.form.get("CallSid")
    user_input = request.form.get("SpeechResult", "")

    if not user_input or call_sid not in conversations:
        resp = VoiceResponse()
        resp.say("Sorry, I didn't catch that.")
        resp.redirect("/voice")
        return str(resp)

    conversations[call_sid].append({"role": "user", "content": user_input})

    # End the call politely if not interested
    if any(kw in user_input.lower() for kw in ["not interested", "goodbye", "no thanks", "stop", "hang up"]):
        resp = VoiceResponse()
        resp.say("No problem. Thanks for your time, have a great day!")
        resp.hangup()
        return str(resp)

    # GPT-4 follow-up
    try:
        reply = openai.ChatCompletion.create(
            model="gpt-4",
            messages=conversations[call_sid]
        )['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[GPT error - /process] {str(e)}")
        reply = "Thanks for sharing that. Our system is designed to help simplify your operations."

    conversations[call_sid].append({"role": "assistant", "content": reply})

    # Generate voice
    audio_url = generate_audio(reply)
    resp = VoiceResponse()

    if audio_url:
        resp.play(audio_url)
    else:
        resp.say(reply)

    gather = Gather(input="speech", action="/process", method="POST", timeout=6)
    gather.say("What are you using today to manage this?")
    resp.append(gather)

    return str(resp)

# Health check route
@app.route("/")
def index():
    return "3DLogistiX AI Voice Agent is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)




