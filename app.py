from flask import Flask, request, send_from_directory, jsonify
from twilio.twiml.voice_response import VoiceResponse, Play
import uuid
import os
from shutil import copyfile

app = Flask(__name__)
STATIC_FOLDER = 'static'

@app.route("/voice", methods=["GET", "POST"])
def voice():
    try:
        # Works for both POST (form data) and GET (query params)
        name = request.values.get("name", "there")
        linkedin = request.values.get("linkedin", "")
        pain = request.values.get("pain", "some operational challenges")

        # Validate required parameters
        if not name or not pain:
            return jsonify({"error": "Missing parameters"}), 400

        # Generate unique MP3 filename
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(STATIC_FOLDER, audio_filename)

        # Simulate TTS generation by copying a sample
        sample_audio = os.path.join(STATIC_FOLDER, "sample.mp3")
        if not os.path.exists(sample_audio):
            return jsonify({"error": "sample.mp3 missing in static/ folder"}), 500
        copyfile(sample_audio, audio_path)

        # Return TwiML XML response
        response = VoiceResponse()
        response.play(f"https://threedlogistix-voice-agent.onrender.com/static/{audio_filename}")
        return str(response), 200, {"Content-Type": "application/xml"}

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)
















