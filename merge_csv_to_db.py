# merge_csv_to_db.py
# FULLY ROBUST MERGE: expenses_income_summary (2).csv → finance.db
# 100% COMPATIBLE WITH YOUR ORM (database.py)

import pandas as pd
import numpy as np
import sqlite3
import uuid
from datetime import datetime
from database import engine, Transaction, init_db
from sqlalchemy.orm import sessionmaker
import os

print("MERGING CSV → finance.db (ORM-Ready, Robust Mode)...")

# -------------------------------
# CONFIG
# -------------------------------
CSV_PATH = "expenses_income_summary (2).csv"
BATCH_SIZE = 1000

if not os.path.exists(CSV_PATH):
    print(f"CSV NOT FOUND: {CSV_PATH}")
    exit()

# -------------------------------
# 1. ROBUST CSV LOADING
# -------------------------------
print("Loading CSV (skip bad lines, Python engine)...")
try:
    csv_df = pd.read_csv(
        CSV_PATH,
        on_bad_lines='skip',
        quoting=3,  # QUOTE_NONE
        engine='python',
        dtype=str  # Read all as string first
    )
    print(f"Raw rows loaded: {len(csv_df)}")
except Exception as e:
    print(f"CSV READ ERROR: {e}")
    exit()

# -------------------------------
# 2. STANDARDIZE COLUMN NAMES
# -------------------------------
print("Standardizing column names...")
csv_df.columns = [col.strip() for col in csv_df.columns]

# Map known variations → standard
col_map = {
    
    'id': 'id',
    'date': 'date',
    'title': 'title',
    'category': 'category',
    'account': 'account',
    'amount': 'amount',
    'currency': 'currency',
    'type': 'type',
    'is_recurring': 'is_recurring',
    'interval': 'interval',
    'created_at': 'created_at'
}

csv_df = csv_df.rename(columns={v: k for k, v in col_map.items() if v in csv_df.columns})

# Required + optional
required = ['date', 'title', 'category','account',  'amount', 'type', 'currency', 'is_recurring', 'interval', 'created_at']
optional = [ 'id']

missing = [col for col in required if col not in csv_df.columns]
if missing:
    print(f"MISSING REQUIRED COLUMNS: {missing}")
    exit()

# Fill optional
for col in optional:
    if col not in csv_df.columns:
        csv_df[col] = np.nan

print(f"Columns mapped: {list(csv_df.columns)}")

# -------------------------------
# 3. CLEAN & PARSE DATA
# -------------------------------
print("Cleaning & parsing data...")

# DATE + TIME (preserve full timestamp)
csv_df['date'] = pd.to_datetime(csv_df['date'], errors='coerce', utc=True)
csv_df = csv_df.dropna(subset=['date'])
csv_df['date'] = csv_df['date'].dt.tz_localize(None)  # Remove timezone

# CREATED_AT
if 'created_at' in csv_df.columns and csv_df['created_at'].notna().any():
    csv_df['created_at'] = pd.to_datetime(csv_df['created_at'], errors='coerce', utc=True)
    csv_df['created_at'] = csv_df['created_at'].dt.tz_localize(None)
else:
    csv_df['created_at'] = pd.Timestamp.now()

# AMOUNT
csv_df['amount'] = pd.to_numeric(csv_df['amount'], errors='coerce')
csv_df = csv_df.dropna(subset=['amount'])

# TYPE
csv_df['type'] = csv_df['type'].astype(str).str.upper().str.strip()
csv_df = csv_df[csv_df['type'].isin(['INCOME', 'EXPENSE'])]

# TITLE & CATEGORY
csv_df['title'] = csv_df['title'].astype(str).str.strip()
csv_df['category'] = csv_df['category'].astype(str).str.strip().str.title()

# ACCOUNT
csv_df['account'] = csv_df['account'].replace(['nan', 'NULL', ''], np.nan).astype(object)

# CURRENCY
csv_df['currency'] = csv_df['currency'].fillna('MYR').str.upper().str.strip()

# IS_RECURRING
csv_df['is_recurring'] = pd.to_numeric(csv_df['is_recurring'], errors='coerce').fillna(0).astype(int)

# INTERVAL
csv_df['interval'] = csv_df['interval'].replace(['NULL', 'null', 'nan', ''], None)

# ID
csv_df['id'] = csv_df['id'].astype(str).str.strip()
csv_df['id'] = csv_df['id'].replace(['nan', '<NA>', 'None', ''], np.nan)
csv_df['id'] = csv_df['id'].fillna(pd.Series([str(uuid.uuid4()) for _ in range(len(csv_df))]))

print(f"Valid rows after cleaning: {len(csv_df)}")

# -------------------------------
# 4. INIT DB & SESSION
# -------------------------------
print("Initializing database...")
init_db()
Session = sessionmaker(bind=engine)
session = Session()

# -------------------------------
# 5. CHECK EXISTING IDs
# -------------------------------
print("Checking for duplicates by ID...")
existing_ids = set()
try:
    result = session.execute("SELECT id FROM transactions").fetchall()
    existing_ids = {row[0] for row in result}
    print(f"Existing IDs in DB: {len(existing_ids)}")
except:
    existing_ids = set()

# Filter out existing
new_df = csv_df[~csv_df['id'].isin(existing_ids)].copy()
skipped = len(csv_df) - len(new_df)
print(f"New records to insert: {len(new_df)} | Skipped (duplicate ID): {skipped}")

# -------------------------------
# 6. BATCH INSERT USING ORM
# -------------------------------
if len(new_df) > 0:
    print(f"Inserting {len(new_df)} new records in batches...")
    for start in range(0, len(new_df), BATCH_SIZE):
        batch = new_df.iloc[start:start+BATCH_SIZE]
        objects = []
        for _, row in batch.iterrows():
            trans = Transaction(
                id=row['id'],
                date=row['date'],
                title=row['title'],
                category=row['category'],
                account=row['account'] if pd.notna(row['account']) else None,
                amount=float(row['amount']),
                currency=row['currency'],
                type=row['type'],
                is_recurring=row['is_recurring'],
                interval=row['interval'],
                created_at=row['created_at']
            )
            objects.append(trans)
        
        session.bulk_save_objects(objects)
        session.commit()
        print(f"  → Batch {start//BATCH_SIZE + 1} inserted")

else:
    print("No new records to insert.")

session.close()

# -------------------------------
# 7. FINAL REPORT
# -------------------------------
total = pd.read_sql("SELECT COUNT(*) as c FROM transactions", engine).iloc[0]['c']

print("\nMERGE COMPLETE!")
print(f"Inserted: {len(new_df)} new records")
print(f"Skipped: {skipped} duplicates (by ID)")
print(f"Total in DB: {total}")
print(f"Database: finance.db")
print("YOUR DATA IS NOW ORM-POWERED & READY!")