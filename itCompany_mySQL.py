import mysql.connector
import threading
import time



mysql_conn = mysql.connector.connect(
    host="localhost",
    user="admin",
    password="Scotianu_2415",
    database="ITCompany_mySQL"
)
mysql_conn.autocommit = False  # Disable autocommit to manually control transactions
# print("Connected to database!")

# =========================== DIRTY READ ===========================
# Problema: O sesiune citește o valoare care nu a fost confirmată (fără commit).
# Isolation Level: READ UNCOMMITTED (Permite citirea datelor nevalidate).
def dirty_read():
    """
        Tranzacția 1:
        1. Modifică valoarea 'role' pentru un angajat.
        2. Nu face COMMIT.

        Tranzacția 2:
        1. Citește valoarea modificată de Tranzacția 1, chiar dacă aceasta nu a fost confirmată.

        Rezultat: Tranzacția 2 poate vedea modificările înainte de commit, ceea ce poate duce la inconsistențe.
    """
    cursor = mysql_conn.cursor()

    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
    cursor.execute("START TRANSACTION;")

    print("\n[Session 1] Modifying role for Employee 1 without commit...")
    cursor.execute("UPDATE employees SET role = 'CEO' WHERE employeeid = 1;")

    def read_dirty():
        time.sleep(1)
        cursor2 = mysql_conn.cursor()
        cursor2.execute("START TRANSACTION;")

        cursor2.execute("SELECT role FROM employees WHERE employeeid = 1;")
        print("[Session 2] Read Dirty Read:", cursor2.fetchone())
        cursor2.close()

    t = threading.Thread(target=read_dirty)
    t.start()

    time.sleep(2)
    print("[Session 1] Performing ROLLBACK...")
    mysql_conn.rollback()
    cursor.close()

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
    cursor = mysql_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Initial read...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    initial_status = cursor.fetchone()
    print("[Session 1] Initial project status:", initial_status)

    def update_status():
        time.sleep(1)
        cursor2 = mysql_conn.cursor()
        cursor2.execute("UPDATE projects SET status = 'Completed' WHERE projectid = 1;")
        mysql_conn.commit()
        print("[Session 2] Updated project status to 'Completed'")
        cursor2.close()

    t = threading.Thread(target=update_status)
    t.start()

    time.sleep(2)

    print("[Session 1] Read after modification...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    new_status = cursor.fetchone()
    print("[Session 1] Status after modification:", new_status)

    cursor.close()
    mysql_conn.commit()

# =========================== PHANTOM READ ===========================
# Problema: Citierea unor rezultate care nu existau la începutul tranzacției.
# Isolation Level: REPEATABLE READ (Asigură consistența rândurilor citite, dar nu blochează inserările noi).
def phantom_read():
    """
       Tranzacția 1:
       1. Citește numărul total de angajați cu rol 'Software Engineer'.

       Tranzacția 2:
       1. Adaugă un nou angajat cu rol 'Software Engineer'.
       2. Face COMMIT.

       Tranzacția 1:
       2. Recitește numărul de angajați cu același rol.

       Rezultat: Tranzacția 1 observă că numărul de rânduri s-a schimbat, deși nu a inserat nimic.
       """
    cursor = mysql_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")

    print("\n[Session 1] Initial read (with LOCKING)...")
    cursor.execute("SELECT COUNT(*) FROM employees WHERE role = 'Software Engineer' FOR UPDATE;")
    initial_count = cursor.fetchone()
    print("[Session 1] Initial number of software engineers:", initial_count)

    def insert_new_employee():
        time.sleep(2)
        cursor2 = mysql_conn.cursor()
        cursor2.execute("INSERT INTO employees (employeeid, name, role) VALUES (4, 'Alex Dumitrescu', 'Software Engineer');")
        mysql_conn.commit()
        print("[Session 2] Added a new Software Engineer.")
        cursor2.close()

    t = threading.Thread(target=insert_new_employee)
    t.start()

    time.sleep(3)

    print("[Session 1] Read after modification...")
    cursor.execute("SELECT COUNT(*) FROM employees WHERE role = 'Software Engineer' FOR UPDATE;")
    new_count = cursor.fetchone()
    print("[Session 1] Final number of software engineers:", new_count)

    cursor.close()
    mysql_conn.commit()

# =========================== LOST UPDATE ===========================
# Problema: Două sesiuni modifică aceeași valoare, dar una dintre modificări este pierdută.
# Isolation Level: READ COMMITTED (Nu protejează împotriva pierderii update-urilor).
def lost_update():
    """
            Tranzacția 1:
            1. Citește statusul proiectului.
            2. Nu face COMMIT.

            Tranzacția 2:
            1. Modifică statusul proiectului la 'Pending'.
            2. Face COMMIT.

            Tranzacția 1:
            3. Modifică statusul la 'In Progress'.
            4. Face COMMIT.

            Rezultat: Tranzacția 1 nu știe de modificarea Tranzacției 2 și poate suprascrie datele fără să știe.
    """
    cursor = mysql_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Initial read...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    initial_status = cursor.fetchone()
    print("[Session 1] Initial project status:", initial_status)

    def update_status():
        time.sleep(1)
        cursor2 = mysql_conn.cursor()
        cursor2.execute("UPDATE projects SET status = 'Pending' WHERE projectid = 1;")
        mysql_conn.commit()
        print("[Session 2] Updated project status to 'Pending'")
        cursor2.close()

    t = threading.Thread(target=update_status)
    t.start()

    time.sleep(2)

    print("[Session 1] Updating to 'In Progress'")
    cursor.execute("UPDATE projects SET status = 'In Progress' WHERE projectid = 1;")
    mysql_conn.commit()

    print("[Session 1] Final project status:", initial_status)

    cursor.close()

# =========================== UNCOMMITTED DEPENDENCY ===========================
# Problema: O tranzacție citește o valoare care ulterior este anulată (rollback).
# Isolation Level: READ COMMITTED (Nu permite citirea datelor neconfirmate, dar nu blochează citirile).
def uncommitted_dependency():
    """
            Tranzacția 1:
            1. Inserează un client, dar nu face COMMIT.

            Tranzacția 2:
            1. Citește lista de clienți.
            2. Găsește clientul inserat de Tranzacția 1.

            Tranzacția 1:
            3. Face ROLLBACK.

            Rezultat: Tranzacția 2 a citit un client care nu mai există după rollback, ducând la inconsistență.
    """
    cursor = mysql_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")

    print("\n[Session 1] Insert client without commit...")
    cursor.execute("INSERT INTO clients (clientid, name) VALUES (4, 'AutoParts SRL');")

    def read_uncommitted():
        time.sleep(1)
        cursor2 = mysql_conn.cursor()
        cursor2.execute("SELECT * FROM clients;")
        print("[Session 2] Read clients:", cursor2.fetchall())
        cursor2.close()

    t = threading.Thread(target=read_uncommitted)
    t.start()

    time.sleep(2)
    print("[Session 1] Performing ROLLBACK...")
    mysql_conn.rollback()

    cursor.close()

# =========================== WRITE SKEW ===========================
# Problema: Două tranzacții verifică o condiție și fac update fără să vadă modificarea celeilalte.
# Isolation Level: SERIALIZABLE (Cel mai strict, dar costisitor în performanță).
def write_skew():
    """
            Tranzacția 1:
            1. Verifică statusul unui proiect (ex: trebuie să fie 'In Progress').

            Tranzacția 2:
            1. Face aceeași verificare și vede același status.
            2. Modifică statusul la 'Completed'.
            3. Face COMMIT.

            Tranzacția 1:
            3. Modifică statusul la 'Cancelled', bazându-se pe date care nu mai sunt corecte.
            4. Face COMMIT.

            Rezultat: Statusul final al proiectului este suprascris într-un mod incorect din cauza unei inconsistențe.
    """
    cursor = mysql_conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

    # Resetăm status-ul proiectului înainte de test
    cursor.execute("UPDATE projects SET status = 'In Progress' WHERE projectid = 1;")
    mysql_conn.commit()
    print("[Session 1] Reset project status to 'In Progress'")

    print("\n[Session 1] Checking project status...")
    cursor.execute("SELECT status FROM projects WHERE projectid = 1;")
    status = cursor.fetchone()[0]
    print("[Session 1] Current project status:", status)

    def second_update():
        time.sleep(1)
        cursor2 = mysql_conn.cursor(buffered=True)

        cursor2.execute("SELECT status FROM projects WHERE projectid = 1;")
        status2 = cursor2.fetchone()[0]
        print("[Session 2] Current project status:", status2)

        if status2 == "In Progress":
            cursor2.execute("UPDATE projects SET status = 'Completed' WHERE projectid = 1;")
            mysql_conn.commit()
            print("[Session 2] Updated project status to 'Completed'.")

        cursor2.close()

    t = threading.Thread(target=second_update)
    t.start()

    time.sleep(2)

    if status == "In Progress":
        cursor.execute("UPDATE projects SET status = 'Cancelled' WHERE projectid = 1;")
        mysql_conn.commit()
        print("[Session 1] Updated project status to 'Cancelled'.")

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

    # Set isolation level once at the start (before transactions)
    mysql_conn.cursor().execute("SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE;")

    cursor = mysql_conn.cursor()
    print("\n[Session 1] Locking clients...")
    cursor.execute("SELECT * FROM clients WHERE clientid = 1 FOR UPDATE;")
    cursor.fetchall()  # Ensure result is read

    def second_transaction():
        time.sleep(1)

        for attempt in range(3):  # Retry up to 3 times if deadlock occurs
            try:
                # Use a separate connection for the second session
                connection2 = mysql.connector.connect(
                    host="localhost",
                    user="admin",
                    password="Scotianu_2415",
                    database="ITCompany_mySQL"
                )
                cursor2 = connection2.cursor()

                print("[Session 2] Locking projects...")
                cursor2.execute("SELECT * FROM projects WHERE projectid = 1 FOR UPDATE;")
                cursor2.fetchall()  # Ensure result is read

                time.sleep(2)

                print("[Session 2] Trying to lock clients...")
                cursor2.execute("SELECT * FROM clients WHERE clientid = 1 FOR UPDATE;")  # Deadlock occurs here
                cursor2.fetchall()  # Ensure result is read

                connection2.commit()
                cursor2.close()
                connection2.close()
                break  # Exit loop if transaction succeeds

            except mysql.connector.errors.InternalError as e:
                if e.errno == 1213:  # Deadlock error code
                    print(f"[Session 2] Deadlock detected. Retrying... (Attempt {attempt+1}/3)")
                    time.sleep(1)  # Small delay before retry
                else:
                    raise  # Re-raise other unexpected errors

    t = threading.Thread(target=second_transaction)
    t.start()

    time.sleep(2)

    for attempt in range(3):  # Retry up to 3 times if deadlock occurs
        try:
            print("[Session 1] Trying to lock projects...")
            cursor.execute("SELECT * FROM projects WHERE projectid = 1 FOR UPDATE;")  # Deadlock occurs here
            cursor.fetchall()  # Ensure result is read

            mysql_conn.commit()
            cursor.close()
            break  # Exit loop if transaction succeeds

        except mysql.connector.errors.InternalError as e:
            if e.errno == 1213:  # Deadlock error code
                print(f"[Session 1] Deadlock detected. Retrying... (Attempt {attempt+1}/3)")
                time.sleep(1)  # Small delay before retry
            else:
                raise  # Re-raise other unexpected erro



# Running tests in MySQL
# print("\n=== Test Dirty Read ===")
# dirty_read()
# print("\n=== Test Unrepeatable Read ===")
# unrepeatable_read()
# print("\n=== Test Phantom Read ===")
# phantom_read()
# print("\n=== Test Lost Update ===")
# lost_update()
# print("\n=== Test Uncommitted Dependency ===")
# uncommitted_dependency()
#print("\n=== Test Write Skew ===")
#write_skew()
print("\n=== Test Deadlock ===")
deadlock()