from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import openai
import os

app = Flask(__name__)

# Set your OpenAI API key (you can also use Render's env vars)
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route("/voice", methods=["POST"])
def voice():
    # Generate GPT-4 response
    prompt = (
        "You are an AI assistant named Alex, calling from 3DLogistiX. "
        "You help warehouse managers understand how 3DLogistiX improves their warehouse efficiency. "
        "Start with a friendly greeting and one impactful line about the product."
    )

    try:
        gpt_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=100
        )
        message = gpt_response['choices'][0]['message']['content'].strip()
    except Exception as e:
        message = "Hi, this is Alex from 3DLogistiX. I’m calling to share how we help warehouses improve efficiency."

    # Respond to the call
    resp = VoiceResponse()
    resp.say(message)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

