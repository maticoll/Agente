# app/utils/datetime_utils.py
from datetime import datetime

def parse_iso8601(date_str: str) -> datetime:
    """
    Intenta parsear cadenas ISO-8601 con o sin zona horaria,
    o bien formatos 'YYYY-MM-DD HH:MM:SS' y 'YYYY-MM-DD'.
    """
    try:
        # Python 3.7+: soporta 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS'
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Intenta con espacios y segundos
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Solo fecha
            return datetime.strptime(date_str, "%Y-%m-%d")
