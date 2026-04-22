import sqlite3
import datetime

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Drop tables if they exist to start fresh
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS transactions')
    cursor.execute('DROP TABLE IF EXISTS alerts')

    # Users table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT DEFAULT 'User'
    )
    ''')

    # Transactions table
    cursor.execute('''
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Alerts table
    cursor.execute('''
    CREATE TABLE alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        reason TEXT NOT NULL,
        severity TEXT DEFAULT 'Low',
        status TEXT DEFAULT 'Open',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transaction_id) REFERENCES transactions (id)
    )
    ''')

    # Seed data
    cursor.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', ('Alice Johnson', 'alice@example.com', 'Admin'))
    cursor.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', ('Bob Smith', 'bob@example.com', 'User'))
    cursor.execute('INSERT INTO users (name, email, role) VALUES (?, ?, ?)', ('Charlie Davis', 'charlie@example.com', 'User'))

    conn.commit()
    conn.close()
    print("Database initialized with updated schema and seed data.")

if __name__ == '__main__':
    init_db()
