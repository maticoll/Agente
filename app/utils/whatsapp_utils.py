import logging
import json
import requests
import os
import tempfile
import openai
import re

from flask import current_app
from app.services.openai_service import generate_response
from app.services.bot_logic import BotLogic

# Inicializar la lógica de fecha
g_logic = BotLogic()

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient: str, text: str) -> dict:
    """
    Construye el payload para enviar un mensaje de texto por WhatsApp.
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text}
    }


def send_message(payload: dict) -> dict:
    """
    Envía un mensaje a través de la Graph API de WhatsApp y registra la respuesta.
    """
    url = f"https://graph.facebook.com/v{current_app.config['GRAPH_API_VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"
    }

    logging.info(f"🚀 [send_message] Payload:\n{payload!r}")
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    if resp.status_code != 200:
        logging.error(f"❌ [send_message] Error {resp.status_code}:\n{resp.text}")
    else:
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        logging.info(f"✅ [send_message] Success, response:\n{body!r}")
    resp.raise_for_status()
    return resp.json()


def process_whatsapp_message(body: dict):
    try:
        msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_type = msg.get("type")
        logging.info(f"📩 Tipo de mensaje recibido: {msg_type}")

        sender = msg["from"]
        if sender == current_app.config["RECIPIENT_WAID"]:
            # Solo procesar #debug de vuelta al bot
            if msg_type == "text" and "#debug" in msg["text"]["body"].lower():
                logging.info("🧪 Procesando #debug interno")
            else:
                return

        contact = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        recipient = contact["wa_id"]
        name = contact["profile"]["name"]

        if msg_type == "text":
            text = msg["text"]["body"]
            logging.info(f"🔎 Procesando texto: {text!r}")

            # 1) Preprocesamiento local
            response = None
            if g_logic.validate_date_format(text):
                response = f"✅ La fecha {text.strip()} es válida."
            elif (day := g_logic.get_day_of_date(text)):
                response = day
            elif (until := g_logic.calculate_days_until(text)):
                response = until

            # 2) Fallback a ChatGPT
            if not response:
                logging.info("   → Ningún handler local, llamando a ChatGPT")
                send_message(get_text_message_input(recipient, "⏳ Consultando API de ChatGPT..."))

                response = generate_response(text, sender, name)
                logging.info(f"   → generate_response retornó: {response!r}")

                send_message(get_text_message_input(recipient, "✅ Respuesta de ChatGPT recibida, enviando mensaje final..."))

            # Normalizar respuesta
            response = str(response)

        elif msg_type == "audio":
            response = handle_audio_message(body)
            if not response:
                response = "❌ Error al procesar audio"

        else:
            response = "⚠️ Solo entiendo texto y audio actualmente."

        payload = get_text_message_input(recipient, response)
        send_message(payload)

    except Exception as e:
        logging.error("❌ Error en process_whatsapp_message:", exc_info=True)


def handle_audio_message(body: dict) -> str | None:
    try:
        msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
        if msg.get("type") != "audio":
            return None
        logging.info("🎙️ Procesando audio")
        media_id = msg["audio"]["id"]
        url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}?access_token={current_app.config['ACCESS_TOKEN']}"
        media_resp = requests.get(url, timeout=10)
        media_resp.raise_for_status()
        audio_url = media_resp.json().get("url")

        audio_data = requests.get(audio_url, timeout=10).content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            tmp.write(audio_data)
            path = tmp.name
        logging.info(f"📁 Audio guardado en {path}")

        with open(path, "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)
        os.remove(path)
        return transcript.get("text")
    except Exception:
        logging.error("❌ Error al procesar audio", exc_info=True)
        return None


def is_valid_whatsapp_message(body: dict) -> bool:
    return (
        body.get("object") and
        body.get("entry") and
        body["entry"][0].get("changes") and
        body["entry"][0]["changes"][0].get("value") and
        body["entry"][0]["changes"][0]["value"].get("messages")
    )
