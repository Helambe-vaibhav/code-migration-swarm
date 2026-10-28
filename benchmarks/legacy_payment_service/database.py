# Legacy Database Layer - Synchronous SQLite with blocking calls
import sqlite3
import time
from models import Account, PaymentRecord

DB_FILE = ":memory:"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (account_id TEXT PRIMARY KEY, balance REAL, currency TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (payment_id TEXT PRIMARY KEY, sender_id TEXT, recipient_id TEXT, amount REAL, status TEXT)''')
    conn.commit()
    conn.close()

def save_account(account):
    conn = get_connection()
    c = conn.cursor()
    # Anti-pattern: string interpolation in raw SQL query
    sql = "INSERT OR REPLACE INTO accounts VALUES ('%s', %f, '%s')" % (account.account_id, account.balance, account.currency)
    c.execute(sql)
    conn.commit()
    conn.close()

def find_account(account_id):
    # Anti-pattern: blocking synchronous sleep simulating slow legacy I/O
    time.sleep(0.01)
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT account_id, balance, currency FROM accounts WHERE account_id = ?", (account_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return Account(row[0], row[1], row[2])
    return None
