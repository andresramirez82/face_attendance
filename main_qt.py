import sys
import cv2
import numpy as np
import base64
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QListWidget, QTableWidget, QTableWidgetItem, 
                             QDialog, QLineEdit, QFormLayout, QMessageBox, QFrame)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QIcon
import qtawesome as qta
import pyttsx3
import threading

from database_manager import DatabaseManager
from face_engine import FaceEngine

class CameraThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.cap = None

    def run(self):
        # Use DirectShow for Windows
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while self._run_flag:
            ret, frame = self.cap.read()
            if ret:
                self.change_pixmap_signal.emit(frame)
            time.sleep(0.01)
        
        if self.cap:
            self.cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class RegistrationThread(QThread):
    progress_signal = pyqtSignal(int, np.ndarray)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, name, dni, email, db, engine):
        super().__init__()
        self.name = name
        self.dni = dni
        self.email = email
        self.db = db
        self.engine = engine
        self._run_flag = True

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        faces_captured = []
        ids_captured = []
        temp_id = len(self.db.get_all_employees()) + 1
        
        count = 0
        while count < 30 and self._run_flag:
            ret, frame = cap.read()
            if not ret: break
            
            faces, gray = self.engine.detect_faces(frame)
            for (x, y, w, h) in faces:
                faces_captured.append(gray[y:y+h, x:x+w])
                ids_captured.append(temp_id)
                count += 1
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            self.progress_signal.emit(count, frame)
            time.sleep(0.05)
            
        cap.release()
        
        if count >= 30:
            # First save to DB and get the REAL ID
            real_id = self.db.add_employee(self.name, self.dni, self.email, np.array([]), "path")
            
            if real_id:
                # Use the real ID for training data
                actual_ids = [real_id] * len(faces_captured)
                self.engine.train_model(faces_captured, actual_ids)
                self.finished_signal.emit(True, f"Empleado registrado con éxito (ID: {real_id})")
            else:
                self.finished_signal.emit(False, "Error al guardar en la base de datos (DNI duplidado?)")
        else:
            self.finished_signal.emit(False, "No se capturaron suficientes muestras de rostro")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FaceTrack Pro - Personnel Management")
        self.setMinimumSize(1100, 700)
        
        self.db = DatabaseManager()
        self.engine = FaceEngine()
        
        self.init_ui()
        self.apply_styles()
        
        self.camera_thread = None
        self.is_camera_running = False
        
        # Detection state
        self.detected_employee_id = None
        self.detected_employee_name = None
        
        # Performance & Stability improvements
        self.last_attendance_time = {} # Cooldown per employee
        self.name_cache = {} # Avoid repeated DB queries every frame
        self.recognition_frame_count = 0 # To skip recognition frames
        
        # Voice Initialization
        try:
            self.voice_engine = pyttsx3.init()
            self.voice_engine.setProperty('rate', 150)
            self.last_voice_time = {} # Cooldown for objects
        except Exception as e:
            print(f"Error voice: {e}")
            self.voice_engine = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(5)
        
        # Logo with icon
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_icon = QLabel("👁️")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet("font-size: 48px;")
        logo_label = QLabel("FaceTrack Pro")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setObjectName("logo")
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_label)
        sidebar_layout.addWidget(logo_container)
        sidebar_layout.addSpacing(30)

        self.btn_fichaje = QPushButton(qta.icon('fa5s.camera', color='#818cf8'), " Fichaje")
        self.btn_empleados = QPushButton(qta.icon('fa5s.users', color='#818cf8'), " Empleados")
        self.btn_reportes = QPushButton(qta.icon('fa5s.chart-bar', color='#818cf8'), " Reportes")

        for btn in [self.btn_fichaje, self.btn_empleados, self.btn_reportes]:
            btn.setCheckable(True)
            btn.setFixedHeight(55)
            btn.setObjectName("navButton")
            sidebar_layout.addWidget(btn)
        
        self.btn_fichaje.setChecked(True)
        sidebar_layout.addStretch()
        
        # Version label
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #475569; font-size: 10px; padding: 10px;")
        sidebar_layout.addWidget(version_label)
        
        main_layout.addWidget(sidebar)

        # Content Area with stretch
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)  # Stretch factor 1 for responsiveness

        # Pages
        self.page_fichaje = self.create_fichaje_page()
        self.page_empleados = self.create_empleados_page()
        self.page_reportes = self.create_reportes_page()

        self.stack.addWidget(self.page_fichaje)
        self.stack.addWidget(self.page_empleados)
        self.stack.addWidget(self.page_reportes)

        # Connections
        self.btn_fichaje.clicked.connect(lambda: self.switch_page(0))
        self.btn_empleados.clicked.connect(lambda: self.switch_page(1))
        self.btn_reportes.clicked.connect(lambda: self.switch_page(2))

    def create_fichaje_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Panel de Fichaje")
        header.setObjectName("header")
        layout.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(20)
        
        # Left: Video - Responsive
        video_container = QFrame()
        video_container.setObjectName("card")
        video_layout = QVBoxLayout(video_container)
        
        # Status indicator
        self.cam_status_indicator = QLabel("● EN VIVO")
        self.cam_status_indicator.setStyleSheet("""
            color: #10b981; 
            font-size: 12px; 
            font-weight: bold;
            padding: 5px;
        """)
        self.cam_status_indicator.setVisible(False)
        video_layout.addWidget(self.cam_status_indicator)
        
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1e293b, stop:1 #0f172a);
            border-radius: 15px;
            border: 2px solid #334155;
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(False)
        video_layout.addWidget(self.video_label, 1)  # Stretch
        content.addWidget(video_container, 2)  # 2/3 of space

        # Right: Controls & History - Responsive
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        # Status Card
        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QVBoxLayout(status_card)
        
        status_header = QLabel("Estado de la Cámara")
        status_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #818cf8;")
        status_layout.addWidget(status_header)
        
        self.status_label = QLabel("Cámara detenida")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        status_layout.addWidget(self.status_label)
        
        self.btn_start_cam = QPushButton(qta.icon('fa5s.play', color='white'), " Iniciar Cámara")
        self.btn_start_cam.setObjectName("primaryButton")
        self.btn_start_cam.clicked.connect(self.toggle_camera)
        status_layout.addWidget(self.btn_start_cam)
        right_panel.addWidget(status_card)
        
        # Employee Detection Card
        detection_card = QFrame()
        detection_card.setObjectName("glassCard")
        detection_layout = QVBoxLayout(detection_card)
        
        detection_header = QLabel("👤 Empleado Detectado")
        detection_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #818cf8;")
        detection_layout.addWidget(detection_header)
        
        self.employee_name_label = QLabel("")
        self.employee_name_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #c7d2fe;
            padding: 5px 0;
        """)
        self.employee_name_label.setWordWrap(True)
        detection_layout.addWidget(self.employee_name_label)
        
        self.last_access_label = QLabel("")
        self.last_access_label.setStyleSheet("""
            font-size: 12px; 
            color: #94a3b8;
            padding: 5px 0;
        """)
        self.last_access_label.setWordWrap(True)
        detection_layout.addWidget(self.last_access_label)
        
        detection_layout.addSpacing(10)
        
        self.btn_entrada = QPushButton(qta.icon('fa5s.sign-in-alt', color='white'), " ENTRADA")
        self.btn_entrada.setObjectName("successButton")
        self.btn_entrada.clicked.connect(lambda: self.register_access("IN"))
        self.btn_entrada.setVisible(False)
        detection_layout.addWidget(self.btn_entrada)
        
        self.btn_salida = QPushButton(qta.icon('fa5s.sign-out-alt', color='white'), " SALIDA")
        self.btn_salida.setObjectName("dangerButton")
        self.btn_salida.clicked.connect(lambda: self.register_access("OUT"))
        self.btn_salida.setVisible(False)
        detection_layout.addWidget(self.btn_salida)
        
        right_panel.addWidget(detection_card)

        # History Card
        history_card = QFrame()
        history_card.setObjectName("card")
        history_layout = QVBoxLayout(history_card)
        
        history_header = QLabel("📋 Últimos Registros")
        history_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #818cf8;")
        history_layout.addWidget(history_header)
        
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        history_layout.addWidget(self.history_list, 1)  # Stretch
        right_panel.addWidget(history_card, 1)  # Takes remaining space
        
        content.addLayout(right_panel, 1)  # 1/3 of space
        layout.addLayout(content, 1)  # Stretch
        return page

    def create_empleados_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Gestión de Empleados"))
        
        self.btn_add_emp = QPushButton("Registrar Nuevo Empleado")
        self.btn_add_emp.clicked.connect(self.open_registration_dialog)
        layout.addWidget(self.btn_add_emp)
        
        self.emp_table = QTableWidget(0, 4)
        self.emp_table.setHorizontalHeaderLabels(["ID", "Nombre", "DNI", "Email"])
        layout.addWidget(self.emp_table)
        
        return page

    def create_reportes_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Reportes de Asistencia"))
        self.report_table = QTableWidget(0, 5)
        self.report_table.setHorizontalHeaderLabels(["Fecha", "Nombre", "Hora", "Tipo", "Estado"])
        layout.addWidget(self.report_table)
        return page

    def switch_page(self, index):
        self.btn_fichaje.setChecked(index == 0)
        self.btn_empleados.setChecked(index == 1)
        self.btn_reportes.setChecked(index == 2)
        self.stack.setCurrentIndex(index)
        
        if index == 1: self.refresh_employees()
        if index == 2: self.refresh_reports()

    def toggle_camera(self):
        if not self.is_camera_running:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        self.camera_thread = CameraThread()
        self.camera_thread.change_pixmap_signal.connect(self.update_image)
        self.camera_thread.start()
        self.is_camera_running = True
        self.btn_start_cam.setText(" Detener Cámara")
        self.btn_start_cam.setIcon(qta.icon('fa5s.stop', color='white'))
        self.status_label.setText("Cámara activa")
        self.cam_status_indicator.setVisible(True)

    def stop_camera(self):
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None
        self.is_camera_running = False
        self.btn_start_cam.setText(" Iniciar Cámara")
        self.btn_start_cam.setIcon(qta.icon('fa5s.play', color='white'))
        self.video_label.clear()
        self.status_label.setText("Cámara detenida")
        self.cam_status_indicator.setVisible(False)
        self.clear_detected_employee()

    def update_image(self, frame):
        self.recognition_frame_count += 1
        
        # Convert to gray for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Only run heavy recognition every 5 frames (~6 times per second)
        if self.recognition_frame_count % 5 == 0:
            faces, _ = self.engine.detect_faces(frame)
            self.last_faces = faces
            self.last_gray = gray
            # NEW: Detect Objects
            self.last_objects = self.engine.detect_objects(frame)
        else:
            faces = getattr(self, 'last_faces', [])
            gray = getattr(self, 'last_gray', gray)
            objects = getattr(self, 'last_objects', [])

        # Process and draw detections
        face_detected = False
        for (x, y, w, h) in faces:
            # Use engine.identify which includes preprocessing
            id_, conf = self.engine.identify(gray[y:y+h, x:x+w])
            if conf < 65:  # Confidence threshold - Increased for better tolerance
                face_detected = True
                if id_ not in self.name_cache:
                    self.name_cache[id_] = self.db.get_employee_name(id_)
                
                name = self.name_cache[id_]
                self.draw_tech_face(frame, x, y, w, h, (0, 255, 0), name)
                
                # Update detection UI (don't auto-register)
                if id_ != self.detected_employee_id:
                    self.update_detected_employee(id_, name)
            else:
                self.draw_tech_face(frame, x, y, w, h, (0, 0, 255), "Desconocido")
        
        # Clear detection if no face found
        if not face_detected and self.detected_employee_id:
            self.clear_detected_employee()

        # Draw and Speak Objects
        objects = getattr(self, 'last_objects', [])
        for obj in objects:
            label = obj["label"]
            conf = obj["confidence"]
            (sx, sy, ex, ey) = obj["box"]
            
            # Draw box
            cv2.rectangle(frame, (sx, sy), (ex, ey), (255, 255, 0), 2)
            cv2.putText(frame, f"{label}", (sx, sy - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # Trigger Voice
            self.announce_object(label)

        # Draw MediaPipe Face Mesh landmarks
        self.engine.draw_face_mesh(frame)

        # Convert to QImage and update UI
        qt_img = self.convert_cv_qt(frame)
        self.video_label.setPixmap(qt_img)

    def draw_tech_face(self, img, x, y, w, h, color, label):
        l = int(w * 0.15)
        t = 2
        
        # Corners (Cyberpunk style)
        # Top-left
        cv2.line(img, (x, y), (x+l, y), color, t)
        cv2.line(img, (x, y), (x, y+l), color, t)
        # Top-right
        cv2.line(img, (x+w, y), (x+w-l, y), color, t)
        cv2.line(img, (x+w, y), (x+w, y+l), color, t)
        # Bottom-left
        cv2.line(img, (x, y+h), (x+l, y+h), color, t)
        cv2.line(img, (x, y+h), (x, y+h-l), color, t)
        # Bottom-right
        cv2.line(img, (x+w, y+h), (x+w-l, y+h), color, t)
        cv2.line(img, (x+w, y+h), (x+w, y+h-l), color, t)
        
        # --- NEW: Digital Scanner Mesh (Look like MediaPipe) ---
        # Draw a subtle grid over the face
        grid_color = (color[0], color[1], color[2])
        alpha = 0.2
        overlay = img.copy()
        
        # Vertical scan lines
        for i in range(1, 4):
            vx = x + int(w * i / 4)
            cv2.line(overlay, (vx, y), (vx, y + h), grid_color, 1)
        # Horizontal scan lines
        for i in range(1, 4):
            vy = y + int(h * i / 4)
            cv2.line(overlay, (x, vy), (x + w, vy), grid_color, 1)
        
        # Scanning line effect (moves with time)
        scan_y = y + int((h * (time.time() * 2 % 1)))
        cv2.line(overlay, (x, scan_y), (x + w, scan_y), color, 2)
        
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        # Elegant label at the bottom
        label_overlay = img.copy()
        cv2.rectangle(label_overlay, (x, y + h + 5), (x + w, y + h + 30), color, -1)
        cv2.addWeighted(label_overlay, 0.4, img, 0.6, 0, img)
        
        cv2.putText(img, label, (x + 10, y + h + 23), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)



    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def announce_object(self, label):
        if self.voice_engine is None:
            return
            
        now = time.time()
        if label not in self.last_voice_time or (now - self.last_voice_time[label] > 5):
            self.last_voice_time[label] = now
            # Run voice in a separate thread to avoid freezing UI
            text = f"He detectado un {label}"
            threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text):
        try:
            # Need to re-init in thread or use a lock if using same engine
            # pyttsx3 is not very thread-safe, let's try a fresh init in thread or just say
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except:
            pass

    def update_detected_employee(self, emp_id, name):
        """Update UI with detected employee information"""
        self.detected_employee_id = emp_id
        self.detected_employee_name = name
        
        # Get last access
        last_access = self.db.get_last_attendance(emp_id)
        
        # Update UI
        self.employee_name_label.setText(name)
        if last_access:
            action_type = "Entrada" if last_access[0] == "IN" else "Salida"
            self.last_access_label.setText(f"Último acceso: {action_type}\n{last_access[1]}")
        else:
            self.last_access_label.setText("Sin registros previos")
        
        # Show buttons
        self.btn_entrada.setVisible(True)
        self.btn_salida.setVisible(True)
        self.status_label.setText("Empleado detectado - Seleccione acción")
    
    def clear_detected_employee(self):
        """Clear detected employee info when face is lost"""
        self.detected_employee_id = None
        self.detected_employee_name = None
        self.employee_name_label.setText("")
        self.last_access_label.setText("")
        self.btn_entrada.setVisible(False)
        self.btn_salida.setVisible(False)
        self.status_label.setText("Esperando cara...")
    
    def register_access(self, action_type):
        """Register attendance when user clicks entrada/salida"""
        if not self.detected_employee_id:
            return
        
        emp_id = self.detected_employee_id
        name = self.detected_employee_name
        
        # Basic schedule logic
        now_time = datetime.now()
        status = "ON_TIME"
        if action_type == "IN" and (now_time.hour > 9 or (now_time.hour == 9 and now_time.minute > 15)):
            status = "LATE"
        
        res = self.db.mark_attendance(emp_id, action_type, status)
        if res:
            self.last_attendance_time[emp_id] = time.time()
            action_text = "Entrada" if action_type == "IN" else "Salida"
            icon = "🔵" if action_type == "IN" else "🔴"
            self.history_list.insertItem(0, f"{icon} {name} - {action_text} - {now_time.strftime('%H:%M:%S')}")
            # Keep history short
            if self.history_list.count() > 20:
                self.history_list.takeItem(20)
            
            self.status_label.setText(f"{action_text} registrada: {name}")
            
            # Clear detection after registration
            self.clear_detected_employee()

    def refresh_employees(self):
        employees = self.db.get_all_employees()
        self.emp_table.setRowCount(len(employees))
        for i, emp in enumerate(employees):
            for j, val in enumerate(emp[:4]):
                self.emp_table.setItem(i, j, QTableWidgetItem(str(val)))

    def refresh_reports(self):
        logs = self.db.get_attendance_report()
        self.report_table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            for j, val in enumerate(log):
                self.report_table.setItem(i, j, QTableWidgetItem(str(val)))

    def open_registration_dialog(self):
        self.stop_camera()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuevo Empleado")
        layout = QFormLayout(dialog)
        
        name_in = QLineEdit()
        dni_in = QLineEdit()
        email_in = QLineEdit()
        
        layout.addRow("Nombre:", name_in)
        layout.addRow("DNI:", dni_in)
        layout.addRow("Email:", email_in)
        
        reg_video = QLabel()
        reg_video.setFixedSize(320, 240)
        reg_video.setStyleSheet("background: black")
        layout.addRow(reg_video)
        
        btn_reg = QPushButton("Escanear y Guardar")
        layout.addRow(btn_reg)
        
        def start_registration():
            self.reg_thread = RegistrationThread(name_in.text(), dni_in.text(), email_in.text(), self.db, self.engine)
            self.reg_thread.progress_signal.connect(lambda count, frame: reg_video.setPixmap(self.convert_cv_qt_small(frame)))
            self.reg_thread.finished_signal.connect(lambda ok, msg: self.on_reg_finished(dialog, ok, msg))
            self.reg_thread.start()
            btn_reg.setEnabled(False)

        btn_reg.clicked.connect(start_registration)
        dialog.exec()

    def convert_cv_qt_small(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(img.scaled(320, 240, Qt.AspectRatioMode.KeepAspectRatio))

    def on_reg_finished(self, dialog, ok, msg):
        QMessageBox.information(self, "Registro", msg)
        if ok: dialog.accept()
        self.refresh_employees()

    def apply_styles(self):
        self.setStyleSheet("""
            /* Main Window */
            QMainWindow { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:1 #1e293b);
            }
            
            /* Sidebar */
            #sidebar { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                border-right: 2px solid #334155;
            }
            #logo { 
                color: #c7d2fe; 
                font-size: 20px; 
                font-weight: bold; 
                padding: 15px;
            }
            
            /* Navigation Buttons */
            #navButton { 
                background-color: transparent; 
                color: #94a3b8; 
                border: none; 
                text-align: left; 
                padding-left: 25px; 
                font-size: 15px;
                border-radius: 10px;
                margin: 5px 10px;
            }
            #navButton:hover { 
                background: rgba(129, 140, 248, 0.1);
                color: #c7d2fe;
            }
            #navButton:checked { 
                color: #c7d2fe; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(99, 102, 241, 0.2), stop:1 rgba(129, 140, 248, 0.1));
                border-left: 4px solid #818cf8;
                font-weight: bold;
            }
            
            /* Headers */
            #header { 
                color: white; 
                font-size: 28px; 
                font-weight: bold; 
                margin: 10px 0;
                padding: 10px 0;
            }
            
            /* Cards */
            #card { 
                background: rgba(30, 41, 59, 0.8);
                border-radius: 16px;
                border: 1px solid rgba(51, 65, 85, 0.8);
                padding: 20px;
            }
            
            #glassCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(99, 102, 241, 0.1), stop:1 rgba(30, 41, 59, 0.6));
                border-radius: 16px;
                border: 2px solid rgba(129, 140, 248, 0.3);
                padding: 20px;
            }
            
            /* Buttons */
            #primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #818cf8);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            #primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
            }
            
            #successButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #34d399);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-weight: bold;
                font-size: 15px;
            }
            #successButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #10b981);
            }
            
            #dangerButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #f87171);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-weight: bold;
                font-size: 15px;
            }
            #dangerButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc2626, stop:1 #ef4444);
            }
            
            /* Labels */
            QLabel { color: #e2e8f0; }
            
            /* Tables */
            QTableWidget { 
                background-color: rgba(30, 41, 59, 0.6);
                color: white;
                border: none;
                gridline-color: #334155;
                border-radius: 10px;
            }
            QHeaderView::section { 
                background-color: #334155;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
            }
            
            /* List Widget */
            #historyList { 
                background-color: transparent;
                color: #cbd5e1;
                border: none;
                font-size: 13px;
            }
            #historyList::item {
                padding: 8px;
                border-radius: 8px;
                margin: 2px 0;
            }
            #historyList::item:hover {
                background-color: rgba(51, 65, 85, 0.5);
            }
            
            /* Input Fields */
            QLineEdit { 
                background-color: #334155;
                color: white;
                border: 2px solid #475569;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #818cf8;
            }
            
            /* Dialogs */
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:1 #1e293b);
            }
        """)
    
    def closeEvent(self, event):
        """Handle window close event - stop camera before closing"""
        if self.is_camera_running:
            self.stop_camera()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
