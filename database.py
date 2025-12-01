# database.py
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, func, update, delete, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date
import os
import hashlib

# -------------------------------
# 1. Setup SQLite Engine
# -------------------------------
DB_PATH = "finance.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}  # ← For Streamlit Cloud
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# -------------------------------
# 2. User model
# -------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=func.now())

# -------------------------------
# 3. Define Transaction Model
# -------------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    date = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    account = Column(String)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="MYR")
    type = Column(String(10), nullable=False)
    is_recurring = Column(Integer, default=0)  # 0 = No, 1 = Yes
    interval = Column(String(10))  # "weekly" or "monthly"
    created_at = Column(DateTime, default=func.now())

# -------------------------------
# 4. Initialize DB (Create Table)
# -------------------------------
def init_db():
    Base.metadata.create_all(engine)

    # ← YOUR EXACT init_users.py LOGIC — ADDED HERE
    with engine.connect() as conn:
        # Create users table if not exists (already done by ORM, but safe)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Insert default admin + demo user (your exact code)
        admin_pass = "admin2025"  # ← You can change this later
        hashed_admin = hashlib.sha256(admin_pass.encode()).hexdigest()
        conn.execute(text("""
            INSERT OR IGNORE INTO users (username, email, password_hash, role) 
            VALUES ('admin', 'admin@myfin.com', :hash, 'admin')
        """), {"hash": hashed_admin})

        hashed_ali = hashlib.sha256("ali123".encode()).hexdigest()
        conn.execute(text("""
            INSERT OR IGNORE INTO users (username, email, password_hash, role) 
            VALUES ('ali', 'ali@gmail.com', :hash, 'user')
        """), {"hash": hashed_ali})

        conn.commit()

# RUN AUTOMATICALLY
init_db()  # ← THIS MAKES IT WORK ON FIRST START

# -------------------------------
# 5. Add New Transaction
# -------------------------------
def add_transaction(data: dict):
    session = SessionLocal()
    try:
        trans = Transaction(**data)
        session.add(trans)
        session.commit()
        return trans.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# -------------------------------
# 6. Get All Transactions as DataFrame
# -------------------------------
def get_transactions_df():
    query = "SELECT id, date, title, category, account, amount, currency, type FROM transactions ORDER BY date DESC"
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])  # Keep as datetime
        df['amount'] = df['amount'].astype(float)
    return df

# -------------------------------
# 7. Get Last N Entries
# -------------------------------
# database.py → get_last_n()
def get_last_n(n: int = 5):
    query = """
    SELECT id, date, title, category, account, amount, currency, type, is_recurring, interval 
    FROM transactions 
    ORDER BY date DESC, created_at DESC 
    LIMIT ?
    """
    df = pd.read_sql(query, engine, params=(n,))
    if not df.empty:
        # KEEP FULL DATETIME WITH TIME
        df['date'] = pd.to_datetime(df['date'])  # ← PRESERVE TIME
        df['amount'] = df['amount'].astype(float)
    return df

# -------------------------------
# 8. Format DataFrame for UI (Title-Case Headers)
# -------------------------------
def format_display_df(df):
    """
    Takes a raw DataFrame from get_last_n() and returns a nicely formatted copy:
    • Date → "2025-10-31 17:44:00"
    • Amount → "1,234.56"
    • Recurring → "Yes"/"No"
    • Column names → Title Case (Date, Title, Category, …)
    """
    df = df.copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["amount"] = df["amount"].apply(lambda x: f"{x:,.2f}")
    df["recurring"] = df["is_recurring"].apply(lambda x: "Yes" if x else "No")

    # Rename to Title Case
    return df.rename(columns={
        "date": "Date",
        "title": "Title",
        "category": "Category",
        "account" : "Account",
        "amount": "Amount",
        "currency": "Currency",
        "type": "Type",
        "recurring": "Recurring"
    })
# ------------------------------
# 9. Delete/Update Transactions
#-------------------------------
def update_transaction(trans_id: str, data: dict):
    session = SessionLocal()
    try:
        stmt = (
            update(Transaction)
            .where(Transaction.id == trans_id)
            .values(**data)
        )
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_transaction(trans_id: str):
    session = SessionLocal()
    try:
        trans = session.query(Transaction).filter(Transaction.id == trans_id).first()
        if trans:
            session.delete(trans)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

