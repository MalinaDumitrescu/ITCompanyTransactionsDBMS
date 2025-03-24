import psycopg2
import threading
import time

# todo postgres nu permite read uncommitted--> nu permit dirty reads


pg_conn = psycopg2.connect(
    dbname="ITCompany_postgres",
    user="admin",
    password="Scotianu_2415",
    host="localhost",
    port="5432"
)
pg_conn.autocommit = False  # Disable autocommit for manual transaction control

# PostgreSQL does NOT allow Dirty Read, so this test is not necessary!

# =========================== UNREPEATABLE READ ===========================
# Problema: Citierea aceleiași valori în cadrul aceleiași tranzacții returnează rezultate diferite.
# Isolation Level: READ COMMITTED (Nu permite citirea datelor nevalidate, dar permite schimbări după commit).
def unrepeatable_read():
    """
        Tranzacția 1:
        1. Citește valoarea 'status' a unui proiect.
        2. Nu face COMMIT.

        Tranzacția 2:
        1. Actualizează statusul proiectului.
        2. Face COMMIT.

        Tranzacția 1:
        3. Citește din nou statusul proiectului.

        Rezultat: Valoarea citită inițial de Tranzacția 1 este diferită de cea citită ulterior.
        """

    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Initial read...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    initial_status = cursor.fetchone()
    print("[Session 1] Initial project status:", initial_status)

    def update_status():
        time.sleep(1)
        cursor2 = pg_conn.cursor()
        cursor2.execute("UPDATE projects SET status = 'Completed' WHERE projectid = 1;")
        pg_conn.commit()
        print("[Session 2] Updated project status to 'Completed'.")
        cursor2.close()

    t = threading.Thread(target=update_status)
    t.start()

    time.sleep(2)

    print("[Session 1] Read after modification...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    new_status = cursor.fetchone()
    print("[Session 1] Project status after modification:", new_status)

    cursor.close()
    pg_conn.commit()

# =========================== PHANTOM READ ===========================
# Problema: Citierea unor rezultate care nu existau la începutul tranzacției.
# Isolation Level: REPEATABLE READ (Asigură consistența rândurilor citite, dar nu blochează inserările noi).
def phantom_read():
    """
        Tranzacția 1:
        1. Citește numărul total de clienți.

        Tranzacția 2:
        1. Adaugă un nou client.
        2. Face COMMIT.

        Tranzacția 1:
        2. Recitește numărul de clienți.

        Rezultat: Tranzacția 1 observă că numărul de rânduri s-a schimbat, deși nu a inserat nimic.
        """
    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")

    print("\n[Session 1] Initial read (with LOCKING)...")

    # ✅ Select all clients with FOR UPDATE to simulate row-level locking
    cursor.execute("SELECT * FROM clients FOR UPDATE;")
    initial_rows = cursor.fetchall()
    print("[Session 1] Initial number of clients:", len(initial_rows))

    def insert_new_client():
        time.sleep(2)
        cursor2 = pg_conn.cursor()

        # ✅ Insert a new client while the first transaction is still open
        cursor2.execute("INSERT INTO clients (clientid, name) VALUES (4, 'Digital Solutions SRL');")
        pg_conn.commit()
        print("[Session 2] Added a new client.")
        cursor2.close()

    t = threading.Thread(target=insert_new_client)
    t.start()

    time.sleep(3)

    print("[Session 1] Read after modification...")
    cursor.execute("SELECT * FROM clients;")
    new_rows = cursor.fetchall()
    print("[Session 1] Final number of clients:", len(new_rows))

    cursor.close()
    pg_conn.commit()

# =========================== LOST UPDATE ===========================
# Problema: Două sesiuni actualizează aceeași valoare, dar una pierde modificarea.
# Isolation Level: READ COMMITTED (Nu protejează împotriva pierderii update-urilor).
def lost_update():
    """
        Tranzacția 1:
        1. Citește valoarea 'status' a unui proiect.

        Tranzacția 2:
        1. Actualizează statusul proiectului.
        2. Face COMMIT.

        Tranzacția 1:
        2. Suprascrie valoarea statusului fără a cunoaște modificarea anterioară.
        3. Face COMMIT.

        Rezultat: Update-ul Tranzacției 2 este pierdut.
        """

    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Initial read...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    initial_status = cursor.fetchone()
    print("[Session 1] Initial project status:", initial_status)

    def update_status():
        time.sleep(1)
        cursor2 = pg_conn.cursor()
        cursor2.execute("UPDATE projects SET status = 'Completed' WHERE projectid = 1;")
        pg_conn.commit()
        print("[Session 2] Updated project status to 'Completed'.")
        cursor2.close()

    t = threading.Thread(target=update_status)
    t.start()

    time.sleep(2)

    print("[Session 1] Updating to 'Cancelled'")
    cursor.execute("UPDATE projects SET status = 'Cancelled' WHERE projectid = 1;")
    pg_conn.commit()

    print("[Session 1] Final project status:", initial_status)

    cursor.close()

def uncommitted_dependency():
    """ Simulates Uncommitted Dependency using the clients table """

    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Insert without commit...")

    # ✅ Check if clientid = 4 exists before inserting
    cursor.execute("SELECT * FROM clients WHERE clientid = 4;")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO clients (clientid, name) VALUES (4, 'Digital Solutions SRL');")
    else:
        print("[Session 1] Skipped insertion, clientid = 4 already exists.")

    def read_uncommitted():
        time.sleep(1)
        cursor2 = pg_conn.cursor()
        cursor2.execute("SELECT * FROM clients;")
        print("[Session 2] Read clients:", cursor2.fetchall())
        cursor2.close()

    t = threading.Thread(target=read_uncommitted)
    t.start()

    time.sleep(2)
    print("[Session 1] Performing ROLLBACK...")
    pg_conn.rollback()

    cursor.close()



def write_skew():
    """ Simulates Write Skew using the clients table """

    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

    print("\n[Session 1] Checking available clients...")
    cursor.execute("SELECT COUNT(*) FROM clients;")
    client_count = cursor.fetchone()[0]
    print("[Session 1] Number of clients:", client_count)

    def second_insert():
        time.sleep(1)
        cursor2 = pg_conn.cursor()
        cursor2.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

        cursor2.execute("SELECT COUNT(*) FROM clients;")
        client_count2 = cursor2.fetchone()[0]
        print("[Session 2] Number of clients:", client_count2)

        if client_count2 < 5:
            cursor2.execute("INSERT INTO clients (clientid, name) VALUES (10, 'Tech Innovators SRL');")
            pg_conn.commit()
            print("[Session 2] Added a new client!")

        cursor2.close()

    t = threading.Thread(target=second_insert)
    t.start()

    time.sleep(2)

    if client_count < 5:
        cursor.execute("INSERT INTO clients (clientid, name) VALUES (11, 'Future Solutions SRL');")
        pg_conn.commit()
        print("[Session 1] Added another client!")

    cursor.close()

# =========================== DEADLOCK ===========================
# Problema: Două sesiuni blochează resurse în ordine inversă, cauzând un blocaj circular.
# Isolation Level: SERIALIZABLE (Cel mai strict, dar predispus la deadlocks).
def deadlock():
    """
        Tranzacția 1:
        1. Blochează tabela 'clients'.

        Tranzacția 2:
        1. Blochează tabela 'projects'.
        2. Încearcă să blocheze tabela 'clients' -> se blochează.

        Tranzacția 1:
        2. Încearcă să blocheze tabela 'projects' -> se blochează.

        Rezultat: Apare un deadlock, iar una dintre tranzacții trebuie să fie anulată.
        """
    cursor = pg_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

    print("\n[Session 1] Locking clients...")
    cursor.execute("SELECT * FROM clients WHERE clientid = 1 FOR UPDATE;")
    cursor.fetchall()  # Ensure result is read

    def second_transaction():
        time.sleep(1)
        cursor2 = pg_conn.cursor()
        cursor2.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

        print("[Session 2] Locking projects...")
        cursor2.execute("SELECT * FROM projects WHERE projectid = 1 FOR UPDATE;")
        cursor2.fetchall()  # Ensure result is read

        time.sleep(2)

        print("[Session 2] Trying to lock clients...")
        cursor2.execute("SELECT * FROM clients WHERE clientid = 1 FOR UPDATE;")  # Deadlock occurs here
        cursor2.fetchall()  # Ensure result is read

        pg_conn.commit()
        cursor2.close()

    t = threading.Thread(target=second_transaction)
    t.start()

    time.sleep(2)

    print("[Session 1] Trying to lock projects...")
    cursor.execute("SELECT * FROM projects WHERE projectid = 1 FOR UPDATE;")  # Deadlock occurs here
    cursor.fetchall()  # Ensure result is read

    pg_conn.commit()
    cursor.close()

# Running tests in PostgreSQL
# print("\n=== Test Unrepeatable Read ===")
#unrepeatable_read()
# print("\n=== Test Phantom Read ===")
#phantom_read()
# print("\n=== Test Lost Update ===")
#lost_update()
#print("\n=== Test Uncommitted Dependency ===")
#uncommitted_dependency()
#print("\n=== Test Write Skew ===")
#write_skew()
#print("\n=== Test Deadlock ===")
#deadlock()