from flask import Flask, request, session
from twilio.twiml.voice_response import VoiceResponse, Play, Gather
import openai
import requests
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "hCjNJSMrJ5BSeizBkC9X")  # default ElevenLabs voice

# Store conversation history in memory
conversations = {}

def generate_speech(text):
    """Generate ElevenLabs TTS audio and return a temporary public URL."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "Authorization": f"Bearer {ELEVEN_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    audio = requests.post(url, headers=headers, json=data)
    filename = f"/tmp/{uuid.uuid4()}.mp3"
    with open(filename, "wb") as f:
        f.write(audio.content)

    upload = requests.post("https://file.io", files={"file": open(filename, "rb")})
    return upload.json().get("link")

@app.route("/voice", methods=["POST"])
def voice():
    call_sid = request.form.get('CallSid')
    conversations[call_sid] = [
        {"role": "system", "content": "You are Alex, an AI sales assistant at 3DLogistiX. Your job is to have a friendly and helpful conversation with warehouse managers. Keep your replies short, clear, and conversational."},
        {"role": "assistant", "content": "Hi, this is Alex from 3DLogistiX. How do you currently manage your warehouse operations?"}
    ]

    intro = conversations[call_sid][-1]['content']
    resp = VoiceResponse()

    try:
        audio_url = generate_speech(intro)
        resp.play(audio_url)
    except:
        gather = Gather(input='speech', action='/process', method='POST', timeout=5)
        gather.say(intro)
        resp.append(gather)

    gather = Gather(input='speech', action='/process', method='POST', timeout=5)
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

@app.route("/process", methods=["POST"])
def process():
    call_sid = request.form.get('CallSid')
    user_input = request.form.get('SpeechResult', '')

    if not user_input or call_sid not in conversations:
        return voice()

    conversations[call_sid].append({"role": "user", "content": user_input})

    # Check for exit
    if any(x in user_input.lower() for x in ["goodbye", "bye", "not interested", "no thanks"]):
        resp = VoiceResponse()
        resp.say("No problem! Thanks for your time. Have a great day.")
        resp.hangup()
        return str(resp)

    try:
        reply = openai.ChatCompletion.create(
            model="gpt-4",
            messages=conversations[call_sid],
            max_tokens=100,
            temperature=0.8
        )['choices'][0]['message']['content'].strip()
    except Exception:
        reply = "Thanks for sharing. We help warehouses like yours improve accuracy and reduce manual tasks."

    conversations[call_sid].append({"role": "assistant", "content": reply})

    resp = VoiceResponse()
    try:
        audio_url = generate_speech(reply)
        resp.play(audio_url)
    except:
        gather = Gather(input='speech', action='/process', method='POST', timeout=5)
        gather.say(reply)
        resp.append(gather)

    gather = Gather(input='speech', action='/process', method='POST', timeout=5)
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
