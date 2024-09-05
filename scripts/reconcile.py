import sqlite3

def store_reconcile(data):
    conn = sqlite3.connect('reconcile.db')
    try:
        cursor = conn.cursor()
        # Insert data using executemany
        cursor.executemany('''
        INSERT INTO reconcile (reconcile_type, content)
        VALUES (?, ?)
        ''', data)

        # # Commit the changes (this is done automatically when using 'with', but can be explicit if needed)
        conn.commit()
    finally:
        conn.close()