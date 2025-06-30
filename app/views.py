import logging
import json

from flask import Blueprint, request, jsonify, current_app
from app.services.scheduler import scheduler  # Importa desde el nuevo módulo

from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)


def handle_message():
    try:
        body = request.get_json(force=True)
    except Exception as e:
        logging.error("❌ Error al parsear JSON con get_json(force=True)")
        logging.error(e)
        body = None
    
    raw_data = request.data
    logging.info(f"📜 Contenido bruto recibido (request.data): {raw_data}")

    # Mostrar payload solo si DEBUG está activado
    if current_app.config.get("DEBUG", False):
        try:
            pretty_body = json.dumps(body, indent=2)
            logging.info(f"🟡 Payload recibido:\n{pretty_body}")
        except Exception as e:
            logging.warning(f"No se pudo formatear el payload: {e}")
            logging.info(f"Payload bruto: {body}")

    # Verifica si es una actualización de estado (sent/delivered/read)
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            logging.info("✅ is_valid_whatsapp_message devolvió True")
            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            logging.warning("❌ Mensaje no válido según is_valid_whatsapp_message")
            return jsonify({"status": "error", "message": "Not a WhatsApp API event"}), 404

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()


@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()


debug_bp = Blueprint("debug", __name__, url_prefix="/_debug")

@debug_bp.route("/jobs")
def list_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat(),
            "func": str(job.func),
            "trigger": str(job.trigger)
        })
    return jsonify(jobs)


# if current_app.config.get("DEBUG", False):
#     @webhook_blueprint.route("/webhook", methods=["GET"])
#     def webhook_post():
#         return handle_message()
# else:
#     @webhook_blueprint.route("/webhook", methods=["POST"])
#     @signature_required
#     @webhook_blueprint.route("/webhook", methods=["POST"])
#     def webhook_post():
#         if current_app.config.get("DEBUG", False):
#             logging.warning("🚨 Ejecutando webhook_post SIN validación de firma (modo DEBUG)")
#             return handle_message()
#         else:
#             from .decorators.security import signature_required
#
#             # Aplicar firma en caliente solo en prod
#             return signature_required(handle_message)()
