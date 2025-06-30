import re
import json

from openai import OpenAI
from flask import current_app
from datetime import timedelta

from app.services.db import get_connection, get_db_path
from app.services.bot_logic import BotLogic
from app.services.customer_service import CustomerService
from app.services.calendar_service import CalendarService
from app.services.scheduler_service import schedule_event_reminder, scheduler
from app.utils.datetime_utils import parse_iso8601


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

    def handle_message(self, message: str, phone: str) -> str:
        # 0) Registramos o buscamos usuario automático
        user = CustomerService.find_or_create(phone)
        self.current_customer_id = user.get("id")
        self.current_phone = phone

        # 1) Preprocesamiento local usando botlogic
        if self.logic.validate_date_format(message):
            if re.search(r"\b(día cae|qué día)\b", message, re.IGNORECASE):
                return self.logic.get_day_of_date(message)
            return self.logic.calculate_days_until(message)

        # Detectar intención de crear evento o consultar clima
        should_create_event = bool(
            re.search(r"\b(agendar|programar|crear evento|reunión|recordar|recordame)\b", message, re.IGNORECASE)
            or re.search(r"\d{1,2}/\d{1,2}/\d{4}", message)
            or re.search(r"\ba\slas\b|\b[0-2]?\d:[0-5]\d", message)
        )
        initial_call = {"name": "create_event"} if should_create_event else "auto"

        # 2) Construcción del prompt para el LLM
        system_prompt = (
            "Eres un asistente de WhatsApp cálido y natural. "
            "Responde con lenguaje claro, directo y humano. "
            "Si el usuario pide clima, eventos o info de cliente, hazlo de forma amistosa. "
            "Evita sonar robótico o enciclopédico. "
            "Si mencionan fecha con hora (ej. '25/6 a las 16:00'), usa toda la info al agendar."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        # 3) Primera llamada al modelo con function-calling
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=self.functions,
            function_call=initial_call
        )
        msg = completion.choices[0].message

        # 4) Si el modelo invocó una función, la ejecutamos
        if getattr(msg, "function_call", None):
            name = msg.function_call.name
            try:
                args = json.loads(msg.function_call.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "lookup_customer":
                args.setdefault("customer_id", self.current_customer_id)

            # Ejecutar la función local
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

        # 5) Si no hubo función, devolvemos el mensaje directo
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

            # 2) Parsear la fecha a datetime (para referenciarlo si hiciera falta)
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

            return {"event_id": event_id, "date": date, "title": title}

    def lookup_customer(self, customer_id: int) -> dict:
        customer = CustomerService.get(customer_id)
        return {"customer": customer}
