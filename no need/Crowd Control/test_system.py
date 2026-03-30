"""
Test Script for Crowd Control System
Simulates crowd detection on sample video or webcam
"""

import os
import cv2
import numpy as np
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.join(os.path.dirname(__file__), ".yolo_config"))
from ultralytics import YOLO
import json
from datetime import datetime

def test_basic_detection():
    """Test basic person detection"""
    print("="*60)
    print("CROWD CONTROL SYSTEM - TEST MODE")
    print("="*60)
    print("\nLoading YOLOv8 model...")
    
    try:
        model = YOLO('yolov8n.pt')
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return
    
    print("\nStarting webcam test...")
    print("Press 'q' to quit")
    
    # Try to open webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("✗ Cannot open webcam")
        print("Tip: Make sure camera is connected and not used by another application")
        return
    
    print("✓ Camera opened successfully")
    
    # Test parameters
    safe_capacity = 10  # Low threshold for testing
    area_sq_meters = 20
    
    frame_count = 0
    detection_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Cannot read frame")
            break
        
        frame_count += 1
        
        # Detect persons every 3 frames for performance
        if frame_count % 3 == 0:
            results = model(frame, classes=0, verbose=False)
            
            person_count = 0
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    if box.conf[0] > 0.4:
                        person_count += 1
                        detection_count += 1
                        
                        # Draw bounding box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cv2.rectangle(frame, 
                                    (int(x1), int(y1)), 
                                    (int(x2), int(y2)), 
                                    (0, 255, 0), 2)
            
            # Calculate metrics
            capacity_percentage = (person_count / safe_capacity) * 100
            density = person_count / area_sq_meters
            
            # Determine alert status
            if capacity_percentage >= 100:
                status = "CRITICAL"
                color = (0, 0, 255)
            elif capacity_percentage >= 85:
                status = "WARNING"
                color = (0, 165, 255)
            else:
                status = "NORMAL"
                color = (0, 255, 0)
            
            # Draw info panel
            cv2.rectangle(frame, (0, 0), (400, 120), (0, 0, 0), -1)
            
            cv2.putText(frame, f"Person Count: {person_count}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Capacity: {capacity_percentage:.1f}%", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, f"Status: {status}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Display frame
        cv2.imshow('Crowd Control Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    print(f"Total frames processed: {frame_count}")
    print(f"Total detections: {detection_count}")
    print(f"Average detections per frame: {detection_count/max(frame_count/3, 1):.2f}")
    print("\n✓ Test completed successfully!")


def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        print("✓ Configuration file loaded successfully")
        print(f"  - Camera sources: {len(config.get('camera_sources', {}))}")
        print(f"  - Alert threshold: {config.get('alert_threshold', 'Not set')}%")
        print(f"  - Alert recipients: {len(config.get('alert_recipients', []))}")
        
    except FileNotFoundError:
        print("✗ Configuration file not found")
        print("  Creating default config.json...")
        create_default_config()
    except json.JSONDecodeError:
        print("✗ Invalid JSON in configuration file")


def create_default_config():
    """Create a default configuration file"""
    default_config = {
        "camera_sources": {
            "test_camera": 0
        },
        "area_dimensions": {
            "test_camera": 50
        },
        "safe_capacity": {
            "test_camera": 120
        },
        "alert_threshold": 0.85,
        "critical_threshold": 1.0,
        "alert_cooldown_seconds": 300
    }
    
    with open('config.json', 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print("✓ Default configuration created")


def test_model_download():
    """Test if model can be downloaded"""
    print("\nTesting model download...")
    
    try:
        model = YOLO('yolov8n.pt')
        print("✓ YOLOv8n model ready")
    except Exception as e:
        print(f"✗ Error with model: {e}")
        print("  The model will be downloaded on first run")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("CROWD CONTROL SYSTEM - COMPREHENSIVE TEST")
    print("="*60)
    
    # Test 1: Model
    test_model_download()
    
    # Test 2: Configuration
    test_configuration()
    
    # Test 3: Detection
    print("\n" + "="*60)
    print("Starting real-time detection test...")
    print("="*60)
    test_basic_detection()


if __name__ == "__main__":
    run_all_tests()
