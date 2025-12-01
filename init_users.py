# init_users.py
import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect("finance.db")
c = conn.cursor()

# Create users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insert default admin (change password!)
admin_pass = "admin2025"  # CHANGE THIS!
c.execute(
    "INSERT OR IGNORE INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
    ("admin", "admin@myfin.com", hash_password(admin_pass), "admin")
)

# Insert demo user
c.execute(
    "INSERT OR IGNORE INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
    ("ali", "ali@gmail.com", hash_password("ali123"), "user")
)

conn.commit()
conn.close()
print("Users table created!")
print("Admin login: admin / admin2025")
print("User login: ali / ali123")