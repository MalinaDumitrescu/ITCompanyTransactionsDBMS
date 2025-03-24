import mysql.connector
import psycopg2
import time

# Conectare la MySQL
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="admin",
    password="Scotianu_2415",
    database="ITCompany_mySQL"
)
mysql_cursor = mysql_conn.cursor()

# Conectare la PostgreSQL
pg_conn = psycopg2.connect(
    dbname="ITCompany_postgres",
    user="admin",
    password="Scotianu_2415",
    host="localhost",
    port="5432"
)
pg_cursor = pg_conn.cursor()


def get_primary_key(cursor, table_name):
    """Obține numele coloanei cheii primare pentru un tabel"""
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.key_column_usage 
        WHERE table_name = %s 
        AND constraint_name LIKE '%%pkey%%'
    """, (table_name,))

    result = cursor.fetchone()
    return result[0] if result else None


def record_exists(cursor, table_name, primary_key, row_id):
    """Verifică dacă un rând există deja în baza de date"""
    cursor.execute(f"SELECT 1 FROM {table_name} WHERE {primary_key} = %s LIMIT 1", (row_id,))
    return cursor.fetchone() is not None


def sync_mysql_to_postgres():
    """Sincronizează modificările din MySQL în PostgreSQL"""
    mysql_cursor.execute("SELECT id, table_name, row_id, operation FROM sync_log ORDER BY timestamp ASC")
    changes = mysql_cursor.fetchall()

    for change in changes:
        log_id, table_name, row_id, operation = change
        primary_key = get_primary_key(mysql_cursor, table_name)

        if not primary_key:
            print(f"⚠️ Nu s-a găsit cheia primară pentru tabelul {table_name}. Salt...")
            continue

        try:
            if operation == 'INSERT':
                if record_exists(pg_cursor, table_name, primary_key, row_id):
                    print(f"🔄 Rândul {row_id} există deja în {table_name}. Se face UPDATE în loc de INSERT.")
                    operation = 'UPDATE'  # Schimbă operația în UPDATE
                else:
                    mysql_cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s", (row_id,))
                    row = mysql_cursor.fetchone()
                    if row:
                        columns = [desc[0] for desc in mysql_cursor.description]
                        col_names = ", ".join(columns)
                        placeholders = ", ".join(["%s"] * len(columns))
                        values = tuple(row)

                        pg_cursor.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", values)

            if operation == 'UPDATE':
                mysql_cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s", (row_id,))
                row = mysql_cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in mysql_cursor.description]
                    update_clause = ", ".join([f"{col} = %s" for col in columns])
                    values = tuple(row) + (row_id,)

                    pg_cursor.execute(f"UPDATE {table_name} SET {update_clause} WHERE {primary_key} = %s", values)

            elif operation == 'DELETE':
                pg_cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key} = %s", (row_id,))

            # Ștergem logul sincronizat
            mysql_cursor.execute("DELETE FROM sync_log WHERE id = %s", (log_id,))
            mysql_conn.commit()
            pg_conn.commit()

        except Exception as e:
            print(f"⚠️ Eroare la sincronizarea {operation} pentru {table_name} (ID: {row_id}):", e)
            pg_conn.rollback()
            mysql_conn.rollback()


def sync_postgres_to_mysql():
    """Sincronizează modificările din PostgreSQL în MySQL"""
    pg_cursor.execute("SELECT id, table_name, row_id, operation FROM sync_log ORDER BY timestamp ASC")
    changes = pg_cursor.fetchall()

    for change in changes:
        log_id, table_name, row_id, operation = change
        primary_key = get_primary_key(pg_cursor, table_name)

        if not primary_key:
            print(f"⚠️ Nu s-a găsit cheia primară pentru tabelul {table_name}. Salt...")
            continue

        try:
            if operation == 'INSERT':
                if record_exists(mysql_cursor, table_name, primary_key, row_id):
                    print(f"🔄 Rândul {row_id} există deja în {table_name}. Se face UPDATE în loc de INSERT.")
                    operation = 'UPDATE'  # Schimbă operația în UPDATE
                else:
                    pg_cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s", (row_id,))
                    row = pg_cursor.fetchone()
                    if row:
                        columns = [desc[0] for desc in pg_cursor.description]
                        col_names = ", ".join(columns)
                        placeholders = ", ".join(["%s"] * len(columns))
                        values = tuple(row)

                        mysql_cursor.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", values)

            if operation == 'UPDATE':
                pg_cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s", (row_id,))
                row = pg_cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in pg_cursor.description]
                    update_clause = ", ".join([f"{col} = %s" for col in columns])
                    values = tuple(row) + (row_id,)

                    mysql_cursor.execute(f"UPDATE {table_name} SET {update_clause} WHERE {primary_key} = %s", values)

            elif operation == 'DELETE':
                mysql_cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key} = %s", (row_id,))

            # Ștergem logul sincronizat
            pg_cursor.execute("DELETE FROM sync_log WHERE id = %s", (log_id,))
            pg_conn.commit()
            mysql_conn.commit()

        except Exception as e:
            print(f"⚠️ Eroare la sincronizarea {operation} pentru {table_name} (ID: {row_id}):", e)
            pg_conn.rollback()
            mysql_conn.rollback()


while True:
    print("🔄 Sincronizare în curs...")
    sync_mysql_to_postgres()
    sync_postgres_to_mysql()
    print("✅ Sincronizare completă. Se așteaptă următoarea rundă...")
    time.sleep(60)  # Rulează sincronizarea la fiecare minut
