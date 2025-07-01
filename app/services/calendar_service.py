from .db import get_connection
from datetime import datetime, date

class CalendarService:
    def __init__(self):
        pass

    def create(self, customer_id: int, date: str, title: str) -> int:
        """
        Inserta un nuevo evento y devuelve su ID.
        - customer_id: ID del cliente que creó el evento.
        - date: fecha y hora en formatos 'YYYY-MM-DD HH:MM', 'YYYY-MM-DDTHH:MM', o 'YYYY-MM-DD'.
        - title: descripción del evento.
        """
        print(f"[DEBUG] Insertando evento con fecha: {date}")
        conn = get_connection()
        cur = conn.cursor()

        # Intentamos parsear fecha y hora sin segundos
        try:
            # Formato "YYYY-MM-DD HH:MM"
            dt = datetime.strptime(date, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # ISO con 'T'
                dt = datetime.fromisoformat(date)
            except ValueError:
                try:
                    # Solo fecha
                    dt = datetime.strptime(date, "%Y-%m-%d")
                except ValueError as e:
                    raise ValueError(f"Formato de fecha inválido: {date}")
        # Guardamos en DB con segundos a 00
        final_date = dt.strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            "INSERT INTO eventos (date, titulo, customer_id) VALUES (?, ?, ?)",
            (final_date, title, customer_id)
        )
        conn.commit()
        event_id = cur.lastrowid
        return event_id

