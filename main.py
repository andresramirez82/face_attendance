import flet as ft
from flet import (
    Icons, Colors, Page, NavigationRail, NavigationRailDestination,
    NavigationRailLabelType, Container, Row, VerticalDivider, Image,
    Text, ListView, Column, ElevatedButton, ListTile, SnackBar,
    DataTable, DataColumn, DataRow, DataCell, TextField, AlertDialog,
    TextButton, MainAxisAlignment, ThemeMode, BoxFit, Icon
)
import cv2
import base64
import numpy as np
import time
import threading
from database_manager import DatabaseManager
from face_engine import FaceEngine
from styles import AppColors, AppStyles

class AttendanceApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = DatabaseManager()
        self.engine = FaceEngine()
        self.page.title = "FaceTrack Pro - Personnel Management"
        self.page.theme_mode = ThemeMode.DARK
        self.page.bgcolor = AppColors.BACKGROUND
        self.page.window_width = 1200
        self.page.window_height = 800
        
        self.running = False
        self.cap = None
        self.detected_employee_id = None
        self.detected_employee_name = None
        
        self.init_ui()

    def init_ui(self):
        # Sidebar Navigation
        self.rail = NavigationRail(
            selected_index=0,
            label_type=NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            bgcolor=AppColors.SURFACE,
            indicator_color=AppColors.PRIMARY,
            destinations=[
                NavigationRailDestination(icon=Icons.CAMERA_ALT_OUTLINED, selected_icon=Icons.CAMERA_ALT, label="Fichaje"),
                NavigationRailDestination(icon=Icons.PEOPLE_OUTLINED, selected_icon=Icons.PEOPLE, label="Empleados"),
                NavigationRailDestination(icon=Icons.ASSESSMENT_OUTLINED, selected_icon=Icons.ASSESSMENT, label="Reportes"),
            ],
            on_change=self.on_nav_change,
        )

        self.content_area = Container(expand=True, padding=20)
        
        self.page.add(
            Row(
                [
                    self.rail,
                    VerticalDivider(width=1),
                    self.content_area,
                ],
                expand=True,
            )
        )
        
        # Default view
        self.show_dashboard()

    def on_nav_change(self, e):
        # Stop camera if running
        self.stop_camera()
        
        if e.control.selected_index == 0:
            self.show_dashboard()
        elif e.control.selected_index == 1:
            self.show_employees()
        elif e.control.selected_index == 2:
            self.show_reports()
        self.page.update()

    def stop_camera(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def show_dashboard(self):
        # Use a local placeholder image to avoid 'src' error
        self.video_image = Image(
            src="placeholder.png", 
            width=800, 
            height=450, 
            fit=BoxFit.CONTAIN, 
            border_radius=15,
            gapless_playback=True # Smoother updates
        )
        self.status_text = Text("Esperando cara...", size=20, color=AppColors.TEXT_SECONDARY)
        self.employee_name_text = Text("", size=24, weight="bold", color=AppColors.PRIMARY)
        self.last_access_text = Text("", size=16, color=AppColors.TEXT_SECONDARY)
        
        self.btn_entrada = ElevatedButton(
            "Registrar ENTRADA", 
            icon=Icons.LOGIN, 
            on_click=lambda _: self.register_access("IN"),
            bgcolor=AppColors.SUCCESS,
            color="white",
            visible=False
        )
        self.btn_salida = ElevatedButton(
            "Registrar SALIDA", 
            icon=Icons.LOGOUT, 
            on_click=lambda _: self.register_access("OUT"),
            bgcolor=AppColors.DANGER,
            color="white",
            visible=False
        )
        
        self.last_log_list = ListView(expand=True, spacing=10)

        self.content_area.content = Column([
            Text("Panel de Fichaje", style=AppStyles.HERO_TEXT),
            Row([
                Container(
                    content=self.video_image,
                    **AppStyles.CARD_STYLE,
                    width=820,
                ),
                Column([
                    Container(
                        content=Column([
                            Text("Estado Cámara", weight="bold"),
                            self.status_text,
                            ElevatedButton("Iniciar Cámara", icon=Icons.PLAY_ARROW, on_click=self.start_clockin_camera),
                            ElevatedButton("Detener", icon=Icons.STOP, on_click=lambda _: self.stop_camera(), bgcolor=AppColors.DANGER, color="white"),
                        ]),
                        **AppStyles.CARD_STYLE,
                        width=300,
                    ),
                    Container(
                        content=Column([
                            Text("Empleado Detectado", weight="bold", size=18),
                            self.employee_name_text,
                            self.last_access_text,
                            Container(height=10),
                            self.btn_entrada,
                            self.btn_salida,
                        ]),
                        **AppStyles.CARD_STYLE,
                        width=300,
                    ),
                    Container(
                        content=Column([
                            Text("Últimos Registros", weight="bold"),
                            self.last_log_list
                        ]),
                        **AppStyles.CARD_STYLE,
                        width=300,
                        height=250,
                    )
                ], expand=True)
            ], spacing=20)
        ])
        self.page.update()

    def start_clockin_camera(self, e=None):
        if self.running: return
        print("Intentando iniciar cámara con DirectShow (640x480)...")
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        # Set resolution for performance and compatibility
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cap.isOpened():
            print("Error: No se pudo abrir la cámara")
            self.status_text.value = "Error: Cámara no encontrada"
            self.status_text.color = AppColors.DANGER
            self.page.update()
            return

        self.running = True
        # Do not clear src, as it causes a validation error in some Flet versions
        self.page.update()
        threading.Thread(target=self.video_feed_thread, daemon=True).start()

    def video_feed_thread(self):
        last_found_id = None
        cooldown = 0
        frame_count = 0
        
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: break
            frame_count += 1

            # Process frame
            faces, gray = self.engine.detect_faces(frame)
            if len(faces) > 0:
                print(f"Rostros detectados: {len(faces)}")
            
            face_detected = False
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (99, 102, 241), 2) # Theme color
                
                # Recognize
                id_, conf = self.engine.identify(gray[y:y+h, x:x+w])
                
                if id_ and conf < 65: # Confidence threshold - Increased for better tolerance
                    face_detected = True
                    # Found someone! Update UI but don't register yet
                    if id_ != last_found_id or time.time() > cooldown:
                        self.update_detected_employee(id_)
                        last_found_id = id_
                        cooldown = time.time() + 3 # 3 sec cooldown for UI updates
                        
                    employee_name = self.db.get_employee_name(id_)
                    cv2.putText(frame, f"{employee_name} ({int(conf)})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Desconocido", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Hide buttons if no face detected
            if not face_detected and self.detected_employee_id:
                self.clear_detected_employee()

            try:
                # Convert to base64 for Flet (using lower quality for speed)
                _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                img_base64 = base64.b64encode(buffer).decode("utf-8")
                self.video_image.src_base64 = img_base64
                
                # Visual feedback that loop is running
                if frame_count % 10 == 0:
                    self.status_text.value = f"Cámara activa - Feed OK ({frame_count})"
                    self.status_text.update()
                
                self.page.update() # Full page update ensures the image visibility changes are rendered
            except Exception as ex:
                if self.running:
                    print(f"Feed error: {ex}")
                break
            time.sleep(0.01)

    def update_detected_employee(self, employee_id):
        """Update UI with detected employee information"""
        self.detected_employee_id = employee_id
        self.detected_employee_name = self.db.get_employee_name(employee_id)
        
        # Get last access
        last_access = self.db.get_last_attendance(employee_id)
        
        # Update UI
        self.employee_name_text.value = self.detected_employee_name
        if last_access:
            action_type = "Entrada" if last_access[0] == "IN" else "Salida"
            self.last_access_text.value = f"Último acceso: {action_type}\n{last_access[1]}"
        else:
            self.last_access_text.value = "Sin registros previos"
        
        # Show buttons
        self.btn_entrada.visible = True
        self.btn_salida.visible = True
        self.status_text.value = "Empleado detectado - Seleccione acción"
        self.status_text.color = AppColors.PRIMARY
        
    def clear_detected_employee(self):
        """Clear detected employee info when face is lost"""
        self.detected_employee_id = None
        self.detected_employee_name = None
        self.employee_name_text.value = ""
        self.last_access_text.value = ""
        self.btn_entrada.visible = False
        self.btn_salida.visible = False
        self.status_text.value = "Esperando cara..."
        self.status_text.color = AppColors.TEXT_SECONDARY
        
    def register_access(self, action_type):
        """Register attendance when user clicks entrada/salida"""
        if not self.detected_employee_id:
            return
            
        employee_id = self.detected_employee_id
        
        # Basic schedule logic: Start time is 09:00
        now = time.localtime()
        current_hour = now.tm_hour
        current_min = now.tm_min
        
        status = "ON_TIME"
        if action_type == "IN" and (current_hour > 9 or (current_hour == 9 and current_min > 15)):
            status = "LATE"
            status_color = AppColors.DANGER
        else:
            status_color = AppColors.SUCCESS

        # Update DB
        self.db.add_attendance(employee_id, action_type, status)
        
        action_text = "Entrada" if action_type == "IN" else "Salida"
        self.status_text.value = f"{action_text} registrada: {self.detected_employee_name}"
        self.status_text.color = status_color
        
        # Add to list
        self.last_log_list.controls.insert(0, 
            Container(
                content=ListTile(
                    leading=Icon(
                        Icons.LOGIN if action_type == "IN" else Icons.LOGOUT,
                        color=status_color
                    ),
                    title=Text(f"{self.detected_employee_name}"),
                    subtitle=Text(f"{action_text} - {time.strftime('%H:%M:%S')} | {status}"),
                ),
                **AppStyles.CARD_STYLE
            )
        )
        
        # Clear detection after registration
        self.clear_detected_employee()
        self.page.update()

    def show_employees(self):
        # Implementation for listing and adding employees
        employees = self.db.get_all_employees()
        
        self.content_area.content = Column([
            Row([
                Text("Gestión de Empleados", style=AppStyles.HERO_TEXT),
                ElevatedButton("Registrar Nuevo", icon=Icons.ADD, on_click=self.open_registration_dialog)
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            Container(
                content=DataTable(
                    columns=[
                        DataColumn(Text("ID")),
                        DataColumn(Text("Nombre")),
                        DataColumn(Text("DNI")),
                        DataColumn(Text("Email")),
                    ],
                    rows=[
                        DataRow(cells=[
                            DataCell(Text(str(emp[0]))),
                            DataCell(Text(emp[1])),
                            DataCell(Text(emp[2])),
                            DataCell(Text(emp[3])),
                        ]) for emp in employees
                    ],
                ),
                **AppStyles.CARD_STYLE
            )
        ])
        self.page.update()

    def open_registration_dialog(self, e):
        print("Intentando abrir diálogo de registro...")
        try:
            name_field = TextField(label="Nombre Completo", width=300)
            dni_field = TextField(label="DNI", width=300)
            email_field = TextField(label="Email", width=300)
            
            def start_scan(e):
                print(f"Iniciando escaneo para {name_field.value}...")
                self.reg_dialog.open = False
                self.page.update()
                threading.Thread(
                    target=self.capture_and_register, 
                    args=(name_field.value, dni_field.value, email_field.value),
                    daemon=True
                ).start()

            self.reg_dialog = AlertDialog(
                modal=True,
                title=Text("Registrar Nuevo Empleado"),
                content=Column([name_field, dni_field, email_field], tight=True, width=320),
                actions=[
                    TextButton("Cancelar", on_click=lambda _: self.close_reg_dialog()),
                    ElevatedButton("Escanear y Guardar", on_click=start_scan)
                ]
            )
            
            self.page.overlay.append(self.reg_dialog)
            self.reg_dialog.open = True
            self.page.update()
            print("Diálogo abierto en overlay.")
        except Exception as ex:
            print(f"Error al abrir diálogo: {ex}")

    def close_reg_dialog(self):
        if hasattr(self, 'reg_dialog'):
            self.reg_dialog.open = False
            self.page.update()

    def capture_and_register(self, name, dni, email):
        print(f"Iniciando escaneo para: {name}")
        
        # Ensure camera is free
        self.stop_camera()
        time.sleep(0.5) # Give it time to release

        # Simple version: Take a few shots and train
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        faces_captured = []
        ids_captured = []
        
        # We'll use a temp employee ID from count + 1
        temp_id = len(self.db.get_all_employees()) + 1
        
        # Capture loop
        count = 0
        
        while count < 30: # Capture 30 samples
            ret, frame = self.cap.read()
            if not ret: break
            
            faces, gray = self.engine.detect_faces(frame)
            for (x, y, w, h) in faces:
                faces_captured.append(gray[y:y+h, x:x+w])
                ids_captured.append(temp_id)
                count += 1
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"Capturando... {count}/30", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Update UI feed
            try:
                _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                img_base64 = base64.b64encode(buffer).decode("utf-8")
                self.video_image.src_base64 = img_base64
                self.page.update()
            except:
                pass
                
            time.sleep(0.05)
        
        self.cap.release()
        
        if faces_captured:
            # Save to DB
            self.db.add_employee(name, dni, email, np.array([]), "path") # Placeholder for actual blobs
            # Train engine
            self.engine.train_model(faces_captured, ids_captured)
            self.page.snack_bar = SnackBar(Text("Empleado registrado y modelo entrenado!"))
            self.page.snack_bar.open = True
            self.show_employees()

    def show_reports(self):
        logs = self.db.get_attendance_report()
        self.content_area.content = Column([
            Text("Reporte de Asistencia", style=AppStyles.HERO_TEXT),
            ListView(
                expand=True,
                controls=[
                    ListTile(
                        title=Text(f"{log[1]} - {log[3]}"),
                        subtitle=Text(f"Fecha: {log[0]} | Status: {log[4]}"),
                        trailing=Icon(Icons.CIRCLE, color=AppColors.SUCCESS if log[4]=="PRESENT" else AppColors.DANGER)
                    ) for log in logs
                ]
            )
        ])
        self.page.update()

def main(page: ft.Page):
    app = AttendanceApp(page)

if __name__ == "__main__":
    ft.app(main)
