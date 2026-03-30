"""
Advanced Crowd Control System with Heatmap and Zone Monitoring
"""

import os
import cv2
import numpy as np
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.join(os.path.dirname(__file__), ".yolo_config"))
from ultralytics import YOLO
import json
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


class AdvancedCrowdControl:
    def __init__(self, config_file='config.json'):
        """Initialize advanced crowd control with heatmap and zones"""
        self.load_config(config_file)
        self.model = YOLO(self.model_path)
        self.heatmap_history = deque(maxlen=30)  # Store last 30 frames
        self.tracking_history = {}
        self.alert_history = []
        print(f"Loaded advanced detection model: {self.model_path}")
        
    def load_config(self, config_file):
        """Load configuration"""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            detection = self.config.get('detection_settings', {})
            self.model_path = self.resolve_model_path(
                detection.get('model_type', 'yolov8n-pose.pt')
            )
        except FileNotFoundError:
            print("Config file not found, using defaults")
            self.config = {}
            self.model_path = 'yolov8n-pose.pt'

    def resolve_model_path(self, model_type):
        """Normalize configured model names to a loadable checkpoint path."""
        if not model_type:
            return 'yolov8n-pose.pt'

        model_path = str(model_type).strip()
        if "." not in model_path.split("/")[-1]:
            model_path = f"{model_path}.pt"

        return model_path
    
    def create_heatmap(self, frame, detections):
        """Create density heatmap from detections"""
        height, width = frame.shape[:2]
        heatmap = np.zeros((height, width), dtype=np.float32)
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # Create gaussian distribution around person
            y, x = np.ogrid[:height, :width]
            mask = np.exp(-((x - center_x)**2 + (y - center_y)**2) / (2 * 50**2))
            heatmap += mask
        
        # Normalize heatmap
        if heatmap.max() > 0:
            heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
        
        return heatmap
    
    def apply_heatmap_overlay(self, frame, heatmap):
        """Apply heatmap as overlay on frame"""
        # Apply colormap
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Blend with original frame
        overlay = cv2.addWeighted(frame, 0.6, heatmap_colored, 0.4, 0)
        
        return overlay
    
    def detect_zones(self, frame, detections, zones):
        """Detect persons in specific zones"""
        zone_counts = {}
        
        for zone in zones:
            zone_name = zone['name']
            polygon = np.array(zone['polygon'], dtype=np.int32)
            capacity = zone['capacity']
            
            count = 0
            for detection in detections:
                x1, y1, x2, y2 = detection['bbox']
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Check if point is inside polygon
                if cv2.pointPolygonTest(polygon, (center_x, center_y), False) >= 0:
                    count += 1
            
            zone_counts[zone_name] = {
                'count': count,
                'capacity': capacity,
                'percentage': (count / capacity * 100) if capacity > 0 else 0,
                'polygon': polygon
            }
        
        return zone_counts
    
    def draw_zones(self, frame, zone_counts):
        """Draw zones on frame with status"""
        for zone_name, data in zone_counts.items():
            polygon = data['polygon']
            count = data['count']
            capacity = data['capacity']
            percentage = data['percentage']
            
            # Color based on capacity
            if percentage >= 100:
                color = (0, 0, 255)  # Red
            elif percentage >= 85:
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            # Draw polygon
            cv2.polylines(frame, [polygon], True, color, 3)
            
            # Calculate centroid for text
            M = cv2.moments(polygon)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Draw zone info
                text = f"{zone_name}: {count}/{capacity}"
                cv2.putText(frame, text, (cx-50, cy-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"{percentage:.0f}%", (cx-30, cy+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame
    
    def track_persons(self, detections, frame_id):
        """Simple tracking of persons across frames"""
        # This is a simplified tracker - for production use SORT or DeepSORT
        current_centers = []
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            current_centers.append(center)
        
        return current_centers
    
    def calculate_flow_direction(self):
        """Calculate crowd flow direction using optical flow"""
        # This would use optical flow to determine movement patterns
        # Helpful for understanding crowd dynamics
        pass
    
    def generate_analytics_report(self, camera_id, start_time, end_time):
        """Generate analytics report for a time period"""
        report = {
            'camera_id': camera_id,
            'period': {
                'start': start_time,
                'end': end_time
            },
            'statistics': {
                'max_count': 0,
                'avg_count': 0,
                'alert_count': len([a for a in self.alert_history 
                                   if a['camera_id'] == camera_id])
            },
            'peak_times': [],
            'recommendations': []
        }
        
        return report
    
    def process_frame_advanced(self, frame, camera_id, zones=None):
        """Process frame with advanced features"""
        # Detect persons
        results = self.model(frame, classes=0, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = box.conf[0].cpu().numpy()
                
                if confidence > 0.4:
                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': float(confidence)
                    })
        
        # Create heatmap
        heatmap = self.create_heatmap(frame, detections)
        
        # Apply heatmap overlay
        frame_with_heatmap = self.apply_heatmap_overlay(frame, heatmap)
        
        # Draw detections
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            cv2.rectangle(frame_with_heatmap, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Process zones if provided
        if zones:
            zone_counts = self.detect_zones(frame, detections, zones)
            frame_with_heatmap = self.draw_zones(frame_with_heatmap, zone_counts)
        
        return frame_with_heatmap, len(detections), heatmap
    
    def create_dashboard(self, stats):
        """Create visualization dashboard"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Crowd count over time
        axes[0, 0].plot(stats['timestamps'], stats['counts'])
        axes[0, 0].set_title('Crowd Count Over Time')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Person Count')
        
        # Capacity utilization
        axes[0, 1].bar(['Current', 'Capacity'], 
                      [stats['current_count'], stats['capacity']])
        axes[0, 1].set_title('Capacity Utilization')
        
        # Alert history
        axes[1, 0].plot(stats['alert_times'], stats['alert_levels'])
        axes[1, 0].set_title('Alert History')
        
        # Zone distribution
        if 'zone_data' in stats:
            zones = list(stats['zone_data'].keys())
            counts = [stats['zone_data'][z]['count'] for z in zones]
            axes[1, 1].bar(zones, counts)
            axes[1, 1].set_title('Zone Distribution')
        
        plt.tight_layout()
        return fig


def main():
    """Main function for advanced system"""
    print("Advanced Crowd Control System")
    print("With Heatmap Visualization and Zone Monitoring")
    
    system = AdvancedCrowdControl('config.json')
    
    # Prefer the primary webcam, then try a couple of common fallback indexes.
    cap = None
    for candidate in (0, 1, 2):
        test_cap = cv2.VideoCapture(candidate)
        if test_cap.isOpened():
            cap = test_cap
            print(f"Using webcam source: {candidate}")
            break
        test_cap.release()

    if cap is None:
        print("Could not open any webcam source (tried 0, 1, 2).")
        return
    
    # Load zones from config if available
    zones = system.config.get('density_zones', {}).get('railway_station_platform1', None)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        processed_frame, person_count, heatmap = system.process_frame_advanced(
            frame, 'test_camera', zones
        )
        
        # Display
        cv2.imshow('Advanced Crowd Control', processed_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
