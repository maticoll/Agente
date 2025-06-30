import sqlite3
from threading import Lock

# Para evitar problemas de concurrencia en Flask
_conn = None
_lock = Lock()

def get_connection():
    global _conn
    if _conn is None:
        # Conexión única para toda la app
        _conn = sqlite3.connect(
            'threads_db.sqlite',
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        _conn.row_factory = sqlite3.Row
    return _conn
def get_db_path() -> str:
    """Devuelve la ruta absoluta de la base de datos SQLite."""
    return "threads_db.sqlite"