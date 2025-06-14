import os
import tempfile
import uuid
from flask import Flask, request, Response, jsonify
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Init OpenAI client
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
        # Use prompt same as in make_calls.py
        prompt = (
            f"You are Alex, a friendly and knowledgeable AI sales assistant from 3DLogistix, calling {name}, "
            f"a warehouse manager. You've seen their LinkedIn profile at {linkedin} and know their key pain point is: '{pain}'. "
            f"Start by validating their potential pain point. Get them to speak about their pain points and show empathy. "
            f"Then explain how companies like Wilde Brands solved similar challenges using the 3DLogistix WMS solution. "
            f"Wilde Brands connects Shopify, Xero, and Starshipit through our platform to automate order flow, stock visibility, "
            f"and managing their warehouse through the 3D view — saving time, seeing where everyone is in the warehouse and reducing human errors. "
            f"Wrap up by offering to book a short call or demo, and mention we also have connectors to other systems like NetSuite, MOYB, and Magento."
        )

        # Call OpenAI to generate script
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        script = completion.choices[0].message.content
        print(f"[INFO] GPT Script: {script}")

        # Send to ElevenLabs for TTS
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

        # Stream audio back to caller
        return Response(
            tts_response.iter_content(chunk_size=4096),
            content_type="audio/mpeg"
        )

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return "Voice agent is up and running!"

if __name__ == '__main__':
    app.run(debug=False, port=10000, host="0.0.0.0")







