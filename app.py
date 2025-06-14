from flask import Flask, request, session
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Required to use session

openai.api_key = os.getenv("OPENAI_API_KEY")

# Store conversation history in memory (not suitable for production)
conversations = {}

@app.route("/voice", methods=["POST"])
def voice():
    call_sid = request.form.get('CallSid')
    conversations[call_sid] = [
        {"role": "system", "content": "You are Alex, an AI sales assistant at 3DLogistiX. Your job is to have a friendly and helpful conversation with warehouse managers. Keep your replies short, clear, and conversational."},
        {"role": "assistant", "content": "Hi, this is Alex from 3DLogistiX. How do you currently manage your warehouse operations?"}
    ]

    resp = VoiceResponse()
    gather = Gather(input='speech', action='/process', method='POST', timeout=5)
    gather.say(conversations[call_sid][-1]['content'])
    resp.append(gather)
    resp.redirect('/voice')  # Repeats prompt if no input
    return str(resp)

@app.route("/process", methods=["POST"])
def process():
    call_sid = request.form.get('CallSid')
    user_input = request.form.get('SpeechResult', '')

    if not user_input or call_sid not in conversations:
        return voice()

    conversations[call_sid].append({"role": "user", "content": user_input})

    # Check for goodbye or end condition
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
    except Exception as e:
        reply = "Thanks for sharing. We help warehouses like yours improve accuracy and reduce manual tasks."

    conversations[call_sid].append({"role": "assistant", "content": reply})

    resp = VoiceResponse()
    gather = Gather(input='speech', action='/process', method='POST', timeout=5)
    gather.say(reply)
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
