# backup_data.py
import sqlite3
import pandas as pd

conn = sqlite3.connect("finance.db")
df = pd.read_sql("SELECT * FROM transactions", conn)
df.to_csv("backup_transactions.csv", index=False)
conn.close()
print("Backup saved to backup_transactions.csv")