from flask import Blueprint, request, jsonify
from app.services.orchestrator import Orchestrator
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
webhook_bp = Blueprint("webhook", __name__)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
orchestrator = Orchestrator(openai_client)

@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", "")
    phone = data.get("from", "")
    response = orchestrator.handle_message(message, phone)
    return jsonify({"reply": response})
