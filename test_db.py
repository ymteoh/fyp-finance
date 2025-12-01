# test_db.py
import sqlite3
import os

print("Checking for finance.db...")

if not os.path.exists("finance.db"):
    print("ERROR: finance.db NOT FOUND!")
    print("Run: python init_db.py first")
else:
    print("finance.db FOUND!")
    try:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            print("TABLES IN DATABASE:")
            for table in tables:
                print("  →", table[0])
        else:
            print("No tables found. Run init_db.py again.")
        conn.close()
    except Exception as e:
        print("ERROR connecting to DB:", e)