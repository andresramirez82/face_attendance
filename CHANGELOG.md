# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-31

### 🚀 Lanzamiento Inicial
Primera versión estable de **FaceTrack Pro**, un sistema de control de asistencia biométrico con interfaz futurista.

### ✨ Características Nuevas
- **Interfaz de Usuario (UI):**
  - Diseño futurista "Glassmorphism" con gradientes oscuros y acentos neón.
  - Layout totalmente responsivo utilizando PyQt6.
  - Panel lateral de navegación con efectos de iluminación.
  - Indicadores de estado de cámara en tiempo real.

- **Reconocimiento Facial:**
  - Implementación de motor híbrido (Detección Haar Cascade + Reconocimiento LBPH).
  - Optimización de parámetros para reducir falsos positivos.
  - Preprocesamiento de imágenes (ecualización de histograma) para mejorar la precisión en distintas condiciones de luz.

- **Control de Asistencia:**
  - **Fichaje Manual Inteligente:** El sistema detecta al usuario pero requiere confirmación manual para "Entrada" o "Salida, evitando registros accidentales.
  - Prevención de doble fichaje mediante temporizadores de enfriamiento (cooldown).
  - Historial de accesos reciente en el dashboard principal con indicadores visuales (🔵/🔴).

- **Gestión de Empleados:**
  - Módulo de registro con captura guiada de 30 muestras faciales.
  - Base de datos local SQLite (`attendance.db`) para almacenamiento seguro y rápido.
  - Lista de empleados registrados con ID interno.

- **Sistema:**
  - Script de lanzamiento automático `run.py`.
  - Cierre seguro de recursos de hardware (cámara) al salir de la aplicación.
  - Manejo de hilos (threading) para evitar congelamientos de la interfaz durante el procesamiento de video.

### 🔧 Técnico
- Integración de `opencv-contrib-python` para algoritmos biométricos.
- Estructura modular: `main_qt.py` (UI), `face_engine.py` (Lógica), `database_manager.py` (Datos).
- Configuración de `.gitignore` para entornos de desarrollo Python.
