from .db import get_connection

class CustomerService:
    @staticmethod
    def get(customer_id: int) -> dict:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, phone, name FROM customers WHERE id = ?",
            (customer_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"error": "Cliente no encontrado"}
        return { key: row[key] for key in row.keys() }

    @staticmethod
    def find_or_create(phone: str) -> dict:
        """
        Busca un cliente por su número de WhatsApp; si no existe, lo crea.
        Devuelve un dict con {id, phone, name}.
        """
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, phone, name FROM customers WHERE phone = ?", (phone,)
        )
        row = cur.fetchone()
        if row:
            return {key: row[key] for key in row.keys()}

        # Si no existe, crearlo con valores por defecto
        cur.execute(
            "INSERT INTO customers (phone, name) VALUES (?, ?)",
            (phone, f"Cliente {phone}")
        )
        conn.commit()
        new_id = cur.lastrowid
        return {"id": new_id, "phone": phone, "name": f"Cliente {phone}"}