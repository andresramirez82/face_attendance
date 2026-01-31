import os
import subprocess
import sys

def run():
    print("Iniciando aplicación (Versión PyQt6 Stable)...")
    # Ensure init_db has been run
    db_path = "attendance.db"
    if not os.path.exists(db_path):
        print("Inicializando base de datos...")
        subprocess.run([sys.executable, "init_db.py"])
    
    # Run main app
    subprocess.run([sys.executable, "main_qt.py"])

if __name__ == "__main__":
    run()
