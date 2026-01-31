import cv2
import time

def test_camera():
    print("Testing cameras...")
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Camera index {i} is WORKING")
                cv2.imwrite(f"test_cam_{i}.jpg", frame)
                print(f"Captured test_cam_{i}.jpg")
            else:
                print(f"Camera index {i} is OPENED but cannot read frame")
            cap.release()
        else:
            print(f"Camera index {i} is NOT available")

if __name__ == "__main__":
    test_camera()
