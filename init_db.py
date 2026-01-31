import sqlite3
import os

def init_db():
    db_path = "attendance.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Employees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dni TEXT UNIQUE NOT NULL,
            email TEXT,
            photo_path TEXT,
            face_encoding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Schedules Table (0-6 for Mon-Sun)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            day_of_week INTEGER, 
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Attendance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action_type TEXT, -- 'IN' or 'OUT'
            status TEXT, -- 'PRESENT', 'LATE', 'LEFT_EARLY'
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    if not os.path.exists("faces"):
        os.makedirs("faces")
    init_db()
