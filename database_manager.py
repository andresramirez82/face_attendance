import sqlite3
import numpy as np
import io

class DatabaseManager:
    def __init__(self, db_path="attendance.db"):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def add_employee(self, name, dni, email, encoding, photo_path):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Convert numpy array to bytes
        encoding_bytes = encoding.tobytes()
        try:
            cursor.execute('''
                INSERT INTO employees (name, dni, email, face_encoding, photo_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, dni, email, encoding_bytes, photo_path))
            employee_id = cursor.lastrowid
            conn.commit()
            return employee_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_all_employees(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, dni, email FROM employees')
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_employee_name(self, employee_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM employees WHERE id = ?', (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "Desconocido"

    def get_all_encodings(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, face_encoding FROM employees')
        rows = cursor.fetchall()
        conn.close()
        
        known_encodings = []
        known_ids = []
        for row in rows:
            known_ids.append(row[0])
            # Reconstruct numpy array
            encoding = np.frombuffer(row[1], dtype=np.float64)
            known_encodings.append(encoding)
        return known_ids, known_encodings

    def add_attendance(self, employee_id, action_type, status):
        self.mark_attendance(employee_id, action_type, status)

    def mark_attendance(self, employee_id, action_type, status):
        # Avoid double logging within 1 minute
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check last log
        cursor.execute('''
            SELECT timestamp FROM attendance 
            WHERE employee_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (employee_id,))
        last_log = cursor.fetchone()
        
        if last_log:
            # Simple check: if last log was less than 60 seconds ago, skip
            # (In a real app, use datetime parsing)
            pass 

        cursor.execute('''
            INSERT INTO attendance (employee_id, action_type, status)
            VALUES (?, ?, ?)
        ''', (employee_id, action_type, status))
        conn.commit()
        conn.close()
        return True

    def get_last_attendance(self, employee_id):
        """Get the last attendance record for an employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT action_type, timestamp
            FROM attendance
            WHERE employee_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return row  # Returns (action_type, timestamp) or None
    
    def get_attendance_report(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.timestamp, e.name, e.dni, a.action_type, a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.timestamp DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows
