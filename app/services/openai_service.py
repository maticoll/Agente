import os
import json
import shelve
import time
import logging
from dotenv import load_dotenv
from openai import OpenAI
from .orchestrator import Orchestrator

# Cargamos variables de entorno
load_dotenv()

# Inicializar cliente de OpenAI con la API Key del entorno
# Elimina la línea siguiente si se prefiere tomar la API Key hardcodeada (no recomendado)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Instanciamos el orchestrator para function-calling
orchestrator = Orchestrator(client)

# (Opcional) Código legacy comentado para beta-assistants y threads
# Mantener este bloque comentado para posible rollback
# def upload_file(path):
#     file = client.files.create(
#         file=open("../../data/airbnb-faq.pdf", "rb"), purpose="assistants"
#     )
#
# def create_assistant(file):
#     assistant = client.beta.assistants.create(
#         name="WhatsApp AirBnb Assistant",
#         instructions="You're a helpful WhatsApp assistant...",
#         tools=[{"type": "retrieval"}],
#         model="gpt-4-1106-preview",
#         file_ids=[file.id],
#     )
#     return assistant
#
# def check_if_thread_exists(wa_id):
#     with shelve.open("threads_db") as threads_shelf:
#         return threads_shelf.get(wa_id, None)
#
# def store_thread(wa_id, thread_id):
#     with shelve.open("threads_db", writeback=True) as threads_shelf:
#         threads_shelf[wa_id] = thread_id
#
# def run_assistant(thread, name):
#     assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)
#     run = client.beta.threads.runs.create(
#         thread_id=thread.id,
#         assistant_id=assistant.id,
#     )
#     while run.status != "completed":
#         time.sleep(0.5)
#         run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
#     messages = client.beta.threads.messages.list(thread_id=thread.id)
#     new_message = messages.data[0].content[0].text.value
#     logging.info(f"Generated message: {new_message}")
#     return new_message


def generate_response(message_body, wa_id, name):
    """
    Genera la respuesta para un mensaje de WhatsApp.
    Utiliza function-calling para delegar lógica al orchestrator.
    """
    try:
        return orchestrator.handle_message(message_body, wa_id)
    except Exception as e:
        logging.error(f"Error en orchestrator: {e}")
        # En caso de fallo, devolvemos un mensaje genérico
        return "Lo siento, ha ocurrido un error procesando tu solicitud. Por favor, intenta nuevamente más tarde."

