from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    resp = VoiceResponse()
    resp.say("Hi, this is Alex from 3DLogistiX. I'm an AI assistant calling to help warehouses improve picking and inventory accuracy. Do you have a moment?")
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
