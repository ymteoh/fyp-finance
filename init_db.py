# init_db.py
from database import init_db
import os

if __name__ == "__main__":
    print("Creating SQLite database...")
    try:
        init_db()
        db_path = "finance.db"
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"SUCCESS: finance.db created!")
            print(f"Location: {os.path.abspath(db_path)}")
            print(f"Size: {size} bytes")
        else:
            print("FAILED: finance.db NOT created.")
    except Exception as e:
        print(f"ERROR: {e}")