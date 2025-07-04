import re
import json
import os
import logging
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo

from openai import OpenAI
from flask import current_app

from app.services.db import get_connection, get_db_path
from app.services.bot_logic import BotLogic
from app.services.customer_service import CustomerService
from app.services.calendar_service import CalendarService
from app.services.scheduler_service import schedule_event_reminder, scheduler
from app.utils.datetime_utils import parse_iso8601


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")

class Orchestrator:
    def __init__(self, client: OpenAI, catalog_path: str = "functions_catalog.json"):
        """
        Orchestrator que centraliza lógica local (botlogic) y function-calling.
        """
        self.client = client
        self.logic = BotLogic()
        # Carga catálogo de funciones para el modelo
        with open(catalog_path, encoding="utf-8") as f:
            self.functions = json.load(f)

    def handle_message(self, message: str, phone: str) -> str | dict:
        # 0) Registramos o buscamos usuario automático
        user = CustomerService.find_or_create(phone)
        self.current_customer_id = user.get("id")
        self.current_phone = phone

        # 1) Preprocesamiento local usando botlogic
        if self.logic.validate_date_format(message):
            if re.search(r"\b(día cae|qué día)\b", message, re.IGNORECASE):
                return self.logic.get_day_of_date(message)
            return self.logic.calculate_days_until(message)

        # 2) Detectar intención de crear evento o consultar clima
        should_create_event = bool(
            re.search(r"\b(agendar|programar|crear evento|reunión|recordar|recordame)\b", message, re.IGNORECASE)
            or re.search(r"\d{1,2}/\d{1,2}/\d{4}", message)
            or re.search(r"\ba\slas\b|\b[0-2]?\d:[0-5]\d", message)
        )
        initial_call = {"name": "create_event"} if should_create_event else "auto"
        # 3) Construcción del prompt
        local_now = datetime.now(ZoneInfo("America/Montevideo"))
        today_str = local_now.strftime("%d/%m/%Y")
        time_str = local_now.strftime("%H:%M")
        system_prompt = (
            "Eres un asistente de WhatsApp cálido y natural. "
            "Responde con lenguaje claro, directo y humano. "
            "Si el usuario pide clima, eventos o info de cliente, hazlo de forma amistosa. "
            "Evita sonar robótico o enciclopédico. "
            "Si te preguntan que puedes hacer responde con las funciones que puedes correr."
            f"Nota: la fecha y hora actuales son {today_str} a las {time_str}."
            "Cuando el usuario pida un recordatorio, sigue estas reglas:\n"
            " 1. Si detectas “dentro de X horas/minutos”, calcula la hora actual y súmale ese intervalo.\n"
            " 2. Si indica fecha con hora (ej. '25/6 a las 16:00'), úsala tal cual para agendar.\n"
            " 3. Si sólo indica fecha sin hora(ej. '3/7 ir al dentista'), responda: “¿A qué hora te gustaría que te recuerde ir al dentista el 3/7?”\n"
            " 4. Si no indica fecha, asume que es para hoy.\n"
            " 5. Si no indica ni fecha ni hora (ej. “Recuérdame ir al super”), devuelva: “¿A qué hora te gustaría que te lo recuerde?”\n"
            " 6. Extrae siempre la actividad a recordar (por ejemplo “ir al supermercado”) y devuelve el timestamp exacto para guardarlo en la BD."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        # 4) Primera llamada al modelo con function-calling
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=self.functions,
            function_call=initial_call
        )
        msg = completion.choices[0].message

        # 5) Si el modelo invocó una función, la ejecutamos
        if getattr(msg, "function_call", None):
            name = msg.function_call.name
            try:
                args = json.loads(msg.function_call.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # Si es invocación de create_event, ejecutamos y devolvemos dict
            if name == "create_event":
                result = self.create_event(**args)
                # Devolvemos el dict para que el template de WhatsApp lo procese
                return {"title": result.get("title"), "date": result.get("date")}

            # Para otras funciones, hacemos el flujo normal
            if name == "lookup_customer":
                args.setdefault("customer_id", self.current_customer_id)
            if hasattr(self, name):
                result = getattr(self, name)(**args)
            else:
                result = {"error": f"Function '{name}' not implemented."}

            # Reinyección para que el LLM genere el mensaje final
            messages.append({"role": "assistant", "content": None, "function_call": {"name": name, "arguments": msg.function_call.arguments}})
            messages.append({"role": "function", "name": name, "content": json.dumps(result)})

            final = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            return final.choices[0].message.content

        # 6) Si no hubo función, devolvemos el mensaje directo
        return msg.content

    # --- Métodos expuestos al LLM ---

    def get_weather(self, location: str, date: str) -> dict:
        # Stub: reemplazar con llamada real a API de clima
        return {"location": location, "forecast": "sunny", "date": date}

    def create_event(self, date: str, title: str) -> dict:
        print(f"[DEBUG] Orchestrator.create_event → customer_id={self.current_customer_id}, date={date}, title={title}")
        # 1) Guarda en la BD, pasando primero el customer_id
        cs = CalendarService()
        event_id = cs.create(
            self.current_customer_id,  # <- customer_id
            date,                      # <- fecha como string "YYYY-MM-DD HH:MM:SS"
            title                      # <- título del evento
        )

        # 2) Parsear la fecha a datetime
        event_dt = parse_iso8601(date)

        # 3) Programar los jobs: recordatorio y notificación al inicio
        db_path = current_app.config["DATABASE_PATH"]
        advance = current_app.config.get("EVENT_ADVANCE", timedelta(minutes=1))

        schedule_event_reminder(
            scheduler,  # instancia de APScheduler
            event_id,
            db_path,
            advance=advance
        )

        # Devolvemos también title y date para templates
        return {"event_id": event_id, "date": date, "title": title}

    def lookup_customer(self, customer_id: int) -> dict:
        customer = CustomerService.get(customer_id)
        return {"customer": customer}
