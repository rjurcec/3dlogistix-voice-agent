from elevenlabs.client import ElevenLabs
import os

# Set up ElevenLabs client with your API key
client = ElevenLabs(
    api_key="sk_b5b7d0ea553e720bee61b26652a84bf41ccddd84e634f3fe"
)

# Message and voice
message = "Hi, we’re preparing your personalized message. Please stay on the line."
voice_id = "LXy8KWda5yk1Vw6sEV6w"  # Your selected voice

# Generate the audio as a stream (generator)
audio_stream = client.text_to_speech.convert(
    voice_id=voice_id,
    model_id="eleven_multilingual_v2",
    text=message,
    optimize_streaming_latency=1,  # Required param
    output_format="mp3_44100_128"  # MP3 format for Twilio
)

# Save the streamed audio to a file
os.makedirs("static", exist_ok=True)
with open("static/preparing.mp3", "wb") as f:
    for chunk in audio_stream:
        f.write(chunk)

print("✅ preparing.mp3 successfully generated and saved to /static.")













