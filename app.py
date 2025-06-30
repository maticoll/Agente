from flask import Flask, request, jsonify
import os
from openai import OpenAI
from app.services.orchestrator import Orchestrator
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Cliente de OpenAI configurado con la API Key
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
orchestrator = Orchestrator(openai_client)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    # Extraer mensaje y número del remitente
    message = data.get("message", "")
    phone = data.get("from", "")
    # Delegar al orquestador
    response = orchestrator.handle_message(message, phone)
    return jsonify({"reply": response})

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)), debug=True)