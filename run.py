import os
from app import create_app
from app.services.scheduler_service import scheduler, reschedule_all_reminders
from app.config import configure_logging

if __name__ == "__main__":
    configure_logging()
    app = create_app()

    # Programar recordatorios pendientes
    reschedule_all_reminders(scheduler, db_path=app.config.get("DATABASE_PATH"))

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
