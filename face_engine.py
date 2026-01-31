import cv2
import os
import numpy as np
import mediapipe as mp
try:
    import mediapipe.solutions.face_mesh as mp_face_mesh
    import mediapipe.solutions.drawing_utils as mp_drawing
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Classes for MobileNetSSD
CLASSES = ["background", "avion", "bicicleta", "pajaro", "bote",
           "botella", "bus", "carro", "gato", "silla", "vaca", "mesa",
           "perro", "caballo", "moto", "persona", "planta", "oveja",
           "sofa", "tren", "monitor"]

class FaceEngine:
    def __init__(self):
        # MediaPipe Face Mesh
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp_face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.7,  # Increased for better quality
                min_tracking_confidence=0.7
            )
            self.mp_drawing = mp_drawing
            self.drawing_spec = self.mp_drawing.DrawingSpec(thickness=1, circle_radius=1, color=(0, 255, 0))
        else:
            self.face_mesh = None
        
        # Create LBPH Face Recognizer with balanced parameters
        # radius=2, neighbors=12 gives good accuracy without being too strict
        # grid_x=8, grid_y=8 provides good detail analysis
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2,
            neighbors=12,
            grid_x=8,
            grid_y=8
        )
        
        # Use better cascade for frontal face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.trained = False
        self.load_model()

        # Object Detection Initializaton
        self.net = None
        if os.path.exists("MobileNetSSD_deploy.prototxt") and os.path.exists("MobileNetSSD_deploy.caffemodel"):
            self.net = cv2.dnn.readNetFromCaffe("MobileNetSSD_deploy.prototxt", "MobileNetSSD_deploy.caffemodel")

    def load_model(self):
        if os.path.exists("trainer.yml"):
            self.recognizer.read("trainer.yml")
            self.trained = True

    def train_model(self, faces, ids):
        """Train model with preprocessed faces for better accuracy"""
        if not faces or not ids:
            return False
        
        # Preprocess all faces before training
        processed_faces = [self.preprocess_face(face) for face in faces]
        
        ids_array = np.array(ids, dtype=np.int32)
        
        if self.trained:
            # Update existing model with new data
            self.recognizer.update(processed_faces, ids_array)
        else:
            # First time training
            self.recognizer.train(processed_faces, ids_array)
            
        self.recognizer.save("trainer.yml")
        self.trained = True
        return True

    def detect_faces(self, frame):
        """Detect faces with standard parameters for maximum compatibility"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # We removed equalizeHist here as it might interfere with some webcams/lighting conditions regarding the trained cascade
        
        # Standard parameters (original working values):
        # scaleFactor=1.1: standard step
        # minNeighbors=5: standard stability
        # minSize=(30, 30): detects smaller faces (further away)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces, gray

    def preprocess_face(self, gray_face):
        """Preprocess face image - Simple version"""
        # Just equalize histogram for contrast, avoiding heavy changes
        # that would invalidate existing trained models
        return cv2.equalizeHist(gray_face)
    
    def identify(self, gray_face):
        """Identify face with preprocessing for better accuracy"""
        if not self.trained:
            return None, 100
        
        # Preprocess the face
        processed_face = self.preprocess_face(gray_face)
        
        id_, confidence = self.recognizer.predict(processed_face)
        
        # LBPH confidence is distance (lower is better)
        # With our optimized parameters:
        # < 40: Excellent match
        # 40-50: Good match
        # 50-60: Fair match
        # > 60: Poor match (likely different person)
        
        return id_, confidence

    def detect_objects(self, frame):
        if self.net is None:
            return []
            
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        self.net.setInput(blob)
        detections = self.net.forward()
        
        found_objects = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                idx = int(detections[0, 0, i, 1])
                # Skip background and person (face recognition handles people)
                if idx == 0 or idx == 15:
                    continue
                
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                
                label = CLASSES[idx]
                found_objects.append({
                    "label": label,
                    "confidence": confidence,
                    "box": (startX, startY, endX, endY)
                })
        return found_objects

    def draw_face_mesh(self, frame):
        if not MEDIAPIPE_AVAILABLE or self.face_mesh is None:
            return frame
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                self.mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(thickness=1, color=(0, 255, 0))
                )
        return frame

    def capture_training_images(self, cap, employee_id, count=30):
        # Helper to capture multiple shots of a new employee
        faces_data = []
        ids_data = []
        captured = 0
        
        while captured < count:
            ret, frame = cap.read()
            if not ret: break
            
            faces, gray = self.detect_faces(frame)
            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]
                faces_data.append(face_roi)
                ids_data.append(employee_id)
                captured += 1
                # Draw progress
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # This would be shown in the UI
            yield frame, captured

        self.train_model(faces_data, ids_data)
