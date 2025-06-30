import sqlite3

conn = sqlite3.connect('threads_db.sqlite')
cur = conn.cursor()

# Eliminar tablas si existen
cur.execute('DROP TABLE IF EXISTS eventos;')
cur.execute('DROP TABLE IF EXISTS customers;')

# Crear tabla de clientes
cur.execute('''
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT NOT NULL UNIQUE
);
''')

# Crear tabla de eventos con relación al cliente
cur.execute('''
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    date TEXT NOT NULL,  -- Aquí usamos TEXT para guardar fecha con hora
    customer_id INTEGER NOT NULL
);
''')

conn.commit()
conn.close()
print("Base de datos inicializada correctamente con soporte de fecha y hora.")
