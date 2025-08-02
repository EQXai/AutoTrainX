#!/usr/bin/env python3
"""Sync PostgreSQL data back to SQLite for easy viewing."""

import sqlite3
import psycopg2
import json

print("🔄 Sincronizando PostgreSQL → SQLite...")

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host="localhost",
    database="autotrainx",
    user="autotrainx",
    password="1234"
)
pg_cursor = pg_conn.cursor()

# Crear/abrir SQLite para visualización
sqlite_conn = sqlite3.connect('DB/executions_view.db')
sqlite_cursor = sqlite_conn.cursor()

# Copiar estructura y datos de executions
pg_cursor.execute("SELECT * FROM executions")
columns = [desc[0] for desc in pg_cursor.description]
rows = pg_cursor.fetchall()

# Crear tabla en SQLite
sqlite_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS executions (
        {', '.join([f'{col} TEXT' for col in columns])}
    )
""")

# Limpiar y copiar datos
sqlite_cursor.execute("DELETE FROM executions")
placeholders = ', '.join(['?' for _ in columns])
sqlite_cursor.executemany(
    f"INSERT INTO executions VALUES ({placeholders})",
    rows
)

print(f"✅ Copiadas {len(rows)} ejecuciones")

# Hacer lo mismo con variations
pg_cursor.execute("SELECT * FROM variations")
if pg_cursor.rowcount > 0:
    columns = [desc[0] for desc in pg_cursor.description]
    rows = pg_cursor.fetchall()
    
    sqlite_cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS variations (
            {', '.join([f'{col} TEXT' for col in columns])}
        )
    """)
    
    sqlite_cursor.execute("DELETE FROM variations")
    placeholders = ', '.join(['?' for _ in columns])
    sqlite_cursor.executemany(
        f"INSERT INTO variations VALUES ({placeholders})",
        rows
    )
    print(f"✅ Copiadas {len(rows)} variaciones")

# Guardar cambios
sqlite_conn.commit()
sqlite_conn.close()
pg_conn.close()

print("\n📁 Base de datos SQLite creada: DB/executions_view.db")
print("🔍 Ahora puedes abrirla con VSCode como antes!")