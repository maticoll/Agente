import sys
import os
from dotenv import load_dotenv
import logging
import requests
from datetime import timedelta  # ← agregado para manejar el intervalo de recordatorios

def validate_access_token(token):
    try:
        resp = requests.get(
            "https://graph.facebook.com/v23.0/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code != 200:
            raise ValueError("El token de acceso de WhatsApp no es válido o está expirado.")
    except Exception as e:
        logging.error(f"[FATAL] Token inválido: {e}")
        raise SystemExit("Abortando: token de WhatsApp inválido.")

def load_configurations(app):
    load_dotenv()

    app.config["ACCESS_TOKEN"]       = os.getenv("ACCESS_TOKEN")
    app.config["YOUR_PHONE_NUMBER"]  = os.getenv("YOUR_PHONE_NUMBER")
    app.config["APP_ID"]             = os.getenv("APP_ID")
    app.config["APP_SECRET"]         = os.getenv("APP_SECRET")
    app.config["RECIPIENT_WAID"]     = os.getenv("RECIPIENT_WAID")
    app.config["VERSION"]            = "v23.0"
    app.config["PHONE_NUMBER_ID"]    = os.getenv("PHONE_NUMBER_ID")
    # Agregamos la versión de la API sin la 'v' delante
    app.config["GRAPH_API_VERSION"]  = os.getenv("GRAPH_API_VERSION", "23.0")
    app.config["VERIFY_TOKEN"]       = os.getenv("VERIFY_TOKEN")
    app.config["DEBUG"]              = os.getenv("DEBUG", "false").lower() == "true"


    # Ubicación de la base de datos SQLite para eventos y customers
    app.config["DATABASE_PATH"]      = os.getenv("DB_PATH", "threads_db.sqlite")

    # Días de antelación para el recordatorio (por defecto 1 día)
    advance_days = int(os.getenv("EVENT_ADVANCE_DAYS", "1"))
    app.config["EVENT_ADVANCE"]      = timedelta(days=advance_days)


    validate_access_token(app.config["ACCESS_TOKEN"])
    logging.info(f"[DEBUG] ACCESS_TOKEN = {app.config['ACCESS_TOKEN'][:10]}...")

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
