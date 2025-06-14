{\rtf1\ansi\ansicpg1252\cocoartf2761
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from flask import Flask, request\
from twilio.twiml.voice_response import VoiceResponse\
\
app = Flask(__name__)\
\
@app.route("/voice", methods=["POST"])\
def voice():\
    resp = VoiceResponse()\
    resp.say("Hi, this is Alex from 3DLogistiX. I'm an AI assistant calling to help warehouses improve picking and inventory accuracy. Do you have a moment?")\
    return str(resp)\
\
if __name__ == "__main__":\
    app.run(host="0.0.0.0", port=10000)\
}