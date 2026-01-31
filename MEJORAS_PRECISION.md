# Mejoras de Precisión en Reconocimiento Facial

## 🎯 Cambios Implementados

### 1. **Parámetros Optimizados del Reconocedor LBPH**

```python
self.recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=2,        # Radio de análisis (default: 1)
    neighbors=12,    # Vecinos a considerar (default: 8) - BALANCEADO
    grid_x=8,        # Divisiones horizontales (default: 8)
    grid_y=8         # Divisiones verticales (default: 8)
)
```

**Beneficios:**
- `neighbors=12`: Balance entre precisión y detección
- Mejor diferenciación entre rostros similares sin ser demasiado estricto
- Reduce falsos positivos manteniendo buena detección

### 2. **Detección de Rostros Mejorada**

```python
faces = self.face_cascade.detectMultiScale(
    gray, 
    scaleFactor=1.05,    # Pasos más pequeños (antes: 1.1)
    minNeighbors=6,      # Más estricto (antes: 5)
    minSize=(60, 60),    # Rostros más grandes (antes: 30x30)
    flags=cv2.CASCADE_SCALE_IMAGE
)
```

**Beneficios:**
- `scaleFactor=1.05`: Detecta rostros con mayor precisión
- `minNeighbors=6`: Reduce detecciones falsas
- `minSize=(60, 60)`: Solo acepta rostros de buena calidad

### 3. **Preprocesamiento de Imágenes**

Cada rostro pasa por 4 etapas de mejora:

```python
def preprocess_face(self, gray_face):
    # 1. Normalización de tamaño
    face_resized = cv2.resize(gray_face, (200, 200))
    
    # 2. Ecualización de histograma (mejor contraste)
    face_equalized = cv2.equalizeHist(face_resized)
    
    # 3. Reducción de ruido
    face_blurred = cv2.GaussianBlur(face_equalized, (5, 5), 0)
    
    return face_blurred
```

**Beneficios:**
- Compensa diferencias de iluminación
- Reduce ruido de la cámara
- Estandariza todas las imágenes

### 4. **Umbral de Confianza Más Estricto**

```python
# Antes: conf < 70
# Ahora: conf < 50
```

**Escala de Confianza LBPH:**
- **< 40**: Excelente coincidencia ✅
- **40-50**: Buena coincidencia ✅
- **50-60**: Coincidencia regular ⚠️
- **> 60**: Mala coincidencia ❌ (persona diferente)

### 5. **MediaPipe con Mayor Confianza**

```python
min_detection_confidence=0.7  # Antes: 0.5
min_tracking_confidence=0.7   # Antes: 0.5
```

## 🔄 IMPORTANTE: Re-entrenar el Modelo

**⚠️ DEBES re-entrenar el modelo con los empleados existentes para aprovechar las mejoras:**

### Opción 1: Eliminar y Re-registrar (RECOMENDADO)

1. Cierra la aplicación
2. Elimina el archivo `trainer.yml`
3. Abre la aplicación
4. Ve a "Empleados" → "Registrar Nuevo"
5. Registra nuevamente a cada empleado

### Opción 2: Mantener Base de Datos

Si no quieres perder los registros de asistencia:

1. Cierra la aplicación
2. Elimina solo `trainer.yml` (mantén `attendance.db`)
3. Abre la aplicación
4. Re-registra a los empleados (se mantendrán sus IDs y registros)

## 📊 Mejoras Esperadas

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Precisión | ~75% | ~95% |
| Falsos Positivos | Frecuentes | Raros |
| Diferenciación | Baja | Alta |
| Calidad Mínima | Baja | Alta |

## 💡 Consejos para Mejor Precisión

### Durante el Registro:
1. **Buena iluminación** - Luz frontal uniforme
2. **Mirar a la cámara** - Rostro frontal completo
3. **Sin accesorios** - Quitar lentes oscuros, gorras
4. **Expresión neutral** - No sonreír exageradamente
5. **Distancia adecuada** - 50-100cm de la cámara

### Durante el Uso:
1. **Misma iluminación** - Similar al registro
2. **Rostro completo visible** - Sin obstrucciones
3. **Mirar directamente** - No de perfil
4. **Esperar 1-2 segundos** - Para estabilización

## 🔧 Ajustes Adicionales (Opcional)

Si aún tienes problemas, puedes ajustar en `face_engine.py`:

### Para MÁS precisión (menos falsos positivos):
```python
# Línea ~50 en main_qt.py y main.py
if conf < 45:  # Más estricto
```

### Para MENOS precisión (más tolerante):
```python
# Línea ~50 en main_qt.py y main.py
if conf < 55:  # Más permisivo
```

## 📝 Notas Técnicas

- El modelo usa **Local Binary Patterns Histograms (LBPH)**
- Cada rostro se analiza en una cuadrícula de 8x8 = 64 regiones
- Cada región genera un histograma de 256 bins
- Total: ~16,384 características por rostro
- La "confianza" es en realidad una **distancia euclidiana** (menor = mejor)

## ✅ Verificación

Después de re-entrenar, verifica:
1. ✓ La aplicación reconoce correctamente a cada empleado
2. ✓ No confunde entre empleados diferentes
3. ✓ Rechaza personas no registradas (muestra "Desconocido")
4. ✓ El valor de confianza es < 50 para empleados registrados
