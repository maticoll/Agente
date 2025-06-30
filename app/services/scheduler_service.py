from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3

# Variables internas
_app = None

# Inicializa y arranca el scheduler independiente del contexto HTTP
scheduler = BackgroundScheduler()
scheduler.start()

def init_scheduler(app):
    """
    Debe llamarse desde create_app para registrar la instancia de Flask
    """
    global _app
    _app = app


def schedule_event_reminder(scheduler, event_id: int, db_path: str, advance: timedelta = timedelta(seconds=30)):
    """
    Programa dos jobs:
      1) Recordatorio `advance` antes del evento.
      2) Notificación justo a la hora del evento.
    """
    # Usamos la app inicializada fuera de contextos HTTP
    if _app is None:
        raise RuntimeError("SchedulerService no iniciado: llama a init_scheduler(app) desde create_app()")
    app = _app

    # Recuperar datos del evento
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.date, e.titulo, c.phone
        FROM eventos e
        JOIN customers c ON e.customer_id = c.id
        WHERE e.id = ?
        """, (event_id,)
    )
    result = cursor.fetchone()
    conn.close()
    if not result:
        return

    event_date_str, title, user_phone = result
    try:
        event_dt = datetime.strptime(event_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        event_dt = datetime.strptime(event_date_str, "%Y-%m-%d %H:%M")

    # 1) Recordatorio anticipado
    reminder_dt = event_dt - advance
    if reminder_dt < datetime.now():
        reminder_dt = datetime.now() + timedelta(seconds=10)

    def _send_reminder():
        with app.app_context():
            from app.utils.whatsapp_utils import send_message, get_text_message_input
            text = f"⏰ ¡Recordatorio! Tenés el evento «{title}» el {event_date_str}."
            payload = get_text_message_input(user_phone, text)
            send_message(payload)

    reminder_job_id = f"reminder_event_{event_id}"
    if scheduler.get_job(reminder_job_id):
        scheduler.remove_job(reminder_job_id)
    scheduler.add_job(
        func=_send_reminder,
        trigger="date",
        run_date=reminder_dt,
        id=reminder_job_id,
        replace_existing=True
    )

    # 2) Notificación al iniciar el evento
    notify_dt = event_dt
    if notify_dt < datetime.now():
        notify_dt = datetime.now() + timedelta(seconds=10)

    def _send_notification():
        with app.app_context():
            from app.utils.whatsapp_utils import send_message, get_text_message_input
            text = f"🚀 ¡Tu evento «{title}» está empezando ahora!"
            payload = get_text_message_input(user_phone, text)
            send_message(payload)

    notify_job_id = f"notify_event_{event_id}"
    if scheduler.get_job(notify_job_id):
        scheduler.remove_job(notify_job_id)
    scheduler.add_job(
        func=_send_notification,
        trigger="date",
        run_date=notify_dt,
        id=notify_job_id,
        replace_existing=True
    )


def reschedule_all_reminders(scheduler, db_path: str):
    """Recorre la base de datos y programa todos los recordatorios y notificaciones."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id, e.date, e.titulo, c.phone
        FROM eventos e
        JOIN customers c ON e.customer_id = c.id
        WHERE e.date >= DATE('now')
        """
    )
    events = cursor.fetchall()
    conn.close()

    for event_id, event_date, title, user_phone in events:
        schedule_event_reminder(
            scheduler=scheduler,
            event_id=event_id,
            db_path=db_path,
            advance=timedelta(seconds=30)
        )
