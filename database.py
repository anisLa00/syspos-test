import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().with_name("syspos.db")


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection