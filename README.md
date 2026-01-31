# FaceTrack Pro 👁️

**Sistema de Control de Asistencia por Reconocimiento Facial**

FaceTrack Pro es una aplicación de escritorio moderna y futurista diseñada para gestionar el control de asistencia de personal mediante biometría facial. Combina una interfaz de usuario de alta tecnología con algoritmos robustos de visión por computadora.

![FaceTrack Pro UI](placeholder_for_screenshot.png)

## ✨ Características Principales

*   **🖥️ UI Futurista & Responsiva:** Interfaz gráfica basada en **PyQt6** con diseño "Glassmorphism", gradientes modernos, animaciones suaves y un layout que se adapta a cualquier tamaño de pantalla.
*   **🤖 Reconocimiento Facial Avanzado:** Utiliza algoritmos LBPH (Local Binary Patterns Histograms) optimizados con detección de rostros en cascada (Haar Cascades) y preprocesamiento de imagen para alta precisión.
*   **⏱️ Control de Asistencia en Tiempo Real:** 
    *   Detección automática de empleados.
    *   **No intrusivo:** No registra automáticamente al detectar, evitando falsos positivos.
    *   **Acción manual:** Botones de "Entrada" 🔵 y "Salida" 🔴 que aparecen dinámicamente al reconocer a un empleado.
*   **📊 Gestión Integral:**
    *   Registro de nuevos empleados con captura automática de muestras faciales.
    *   Base de datos SQLite local (`attendance.db`).
    *   Reportes de asistencia y visualización de historial en tiempo real.
*   **⚙️ Estabilidad:** Cierre automático de recursos de cámara y manejo de hilos para una interfaz fluida.

## 🛠️ Tecnologías Utilizadas

*   **Python:** Lenguaje principal.
*   **PyQt6:** Framework para la interfaz gráfica moderna.
*   **OpenCV (cv2):** Procesamiento de imágenes y visión por computadora.
*   **SQLite:** Base de datos ligera y local.
*   **Qtawesome:** Iconografía vectorial moderna.

## 📋 Requisitos Previos

Necesitas tener Python 3.8+ instalado.

Las dependencias principales son:
*   `opencv-contrib-python` (incluye módulos de cara como LBPH)
*   `PyQt6`
*   `numpy`
*   `qtawesome`
*   `flet` (para la versión web alternativa)

## 🚀 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/face-attendance-app.git
    cd face-attendance-app
    ```

2.  **Crear un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    # En Windows:
    .\venv\Scripts\activate
    # En Mac/Linux:
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install opencv-contrib-python PyQt6 numpy qtawesome flet mediapipe
    ```

4.  **Ejecutar la aplicación:**
    Utiliza el script `run.py` que se encarga de lanzar la versión principal (PyQt6):
    ```bash
    python run.py
    ```

## 📖 Guía de Uso

1.  **Inicio:** Al abrir la app, verás el panel principal. La cámara estará detenida por defecto.
2.  **Activar Cámara:** Presiona "Iniciar Cámara". El indicador "EN VIVO" se encenderá.
3.  **Registro de Empleado:**
    *   Ve a la pestaña "Empleados".
    *   Haz clic en "Registrar Nuevo Empleado".
    *   Llena los datos y sigue las instrucciones para capturar el rostro (se tomarán 30 muestras).
4.  **Fichaje:**
    *   En el panel "Fichaje", cuando un empleado registrado se paré frente a la cámara, el sistema mostrará su nombre y último acceso.
    *   Aparecerán botones para registrar **Entrada** o **Salida**.
    *   Al hacer clic, se guarda el registro y se actualiza el historial.

## 🧠 Mejoras de Precisión

El sistema incluye optimizaciones en `face_engine.py` para mejorar la detección:
*   Preprocesamiento de imágenes (Ecualización de histograma).
*   Ajuste de parámetros `scaleFactor` y `minNeighbors` para equilibrar detección y precisión.
*   Consulta el archivo `MEJORAS_PRECISION.md` para detalles técnicos avanzados.

## 📂 Estructura del Proyecto

```
face_attendance_app/
├── main_qt.py          # Aplicación principal (PyQt6) - UI Moderna
├── main.py             # Versión alternativa (Flet)
├── face_engine.py      # Lógica de reconocimiento facial
├── database_manager.py # Manejo de base de datos SQLite
├── run.py              # Script lanzador
├── styles.py           # Estilos (Flet)
├── MEJORAS_PRECISION.md # Documentación técnica
└── ...
```

## 📝 Licencia

Este proyecto es de uso personal y educativo.
