"""
Crowd Control System - Real-time Person Detection and Density Monitoring
Uses YOLOv8 for person detection and analyzes crowd density to prevent stampedes
"""

import csv
import os
import cv2
import numpy as np
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.join(os.path.dirname(__file__), ".yolo_config"))
from ultralytics import YOLO
import json
from datetime import datetime
import threading
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

class CrowdControlSystem:
    def __init__(self, config_file='config.json'):
        """Initialize the crowd control system with configuration"""
        self.load_config(config_file)
        self.model = YOLO(self.model_path)
        # Minimum number of keypoints (conf > 0.3) required to accept a detection
        self.min_valid_keypoints = 4  # Balanced: catches close/seated persons but rejects bags/objects
        # Keypoint indices for left/right shoulders (COCO format)
        self._shoulder_indices = (5, 6)
        self.alert_queue = queue.Queue()
        self.alert_cooldown = {}
        self.is_running = False

        # ── CSV logging: one file per session, write every 10 seconds ────────
        self.csv_log_interval = 10          # seconds between CSV rows
        self._last_csv_log    = {}          # camera_id → last log timestamp
        self.csv_file         = self._init_csv()
        print(f"Loaded detection model: {self.model_path}")
        
    # ──────────────────────────────────────────────────────────────────────────
    # CSV logging
    # ──────────────────────────────────────────────────────────────────────────

    def _init_csv(self):
        """
        Create (or append to) a session CSV file named with today's date.
        Returns the path string so callers know where data is being written.
        """
        os.makedirs('logs', exist_ok=True)
        date_str  = datetime.now().strftime('%Y-%m-%d')
        csv_path  = os.path.join('logs', f'crowd_count_{date_str}.csv')
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'timestamp', 'camera_id', 'person_count',
                    'safe_capacity', 'capacity_pct', 'density_per_sqm',
                    'area_sq_meters', 'alert_level'
                ])

        print(f"✓ CSV log → {os.path.abspath(csv_path)}")
        return csv_path

    def log_person_count_csv(self, camera_id, alert_data):
        """
        Append one row to the CSV if at least csv_log_interval seconds have
        passed since the last write for this camera.
        """
        now = time.time()
        if now - self._last_csv_log.get(camera_id, 0) < self.csv_log_interval:
            return   # not yet time

        self._last_csv_log[camera_id] = now
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        row = [
            timestamp,
            camera_id,
            alert_data['person_count'],
            alert_data['safe_capacity'],
            f"{alert_data['capacity_percentage']:.2f}",
            f"{alert_data['density']:.4f}",
            alert_data['area_sq_meters'],
            alert_data['alert_level'] or 'NORMAL'
        ]

        with open(self.csv_file, 'a', newline='') as f:
            csv.writer(f).writerow(row)

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.area_dimensions = config.get('area_dimensions', {})
                self.safe_capacity = config.get('safe_capacity', {})
                self.alert_threshold = config.get('alert_threshold', 0.9)  # 90% of capacity
                self.critical_threshold = config.get('critical_threshold', 1.0)  # 100% of capacity
                self.alert_recipients = config.get('alert_recipients', [])
                self.camera_sources = config.get('camera_sources', {})
                self.alert_cooldown_seconds = config.get('alert_cooldown_seconds', 300)
                detection = config.get('detection_settings', {})
                self.conf_threshold = float(detection.get('confidence_threshold', 0.40))
                self.model_path = self.resolve_model_path(
                    detection.get('model_type', 'yolov8n-pose.pt')
                )
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Using defaults.")
            self.set_default_config()
    
    def set_default_config(self):
        """Set default configuration"""
        self.area_dimensions = {'default': 50}  # sq meters
        self.safe_capacity = {'default': 120}
        self.alert_threshold = 0.9
        self.critical_threshold = 1.0
        self.alert_recipients = []
        self.camera_sources = {}
        self.alert_cooldown_seconds = 300
        self.conf_threshold = 0.40
        self.model_path = 'yolov8n-pose.pt'

    def resolve_model_path(self, model_type):
        """Normalize configured model names to a loadable checkpoint path."""
        if not model_type:
            return 'yolov8n-pose.pt'

        model_path = str(model_type).strip()
        if not os.path.splitext(model_path)[1]:
            model_path = f"{model_path}.pt"

        return model_path

    def build_source_candidates(self, source):
        """Return the configured source plus sensible webcam fallbacks."""
        candidates = [source]

        if isinstance(source, int):
            for webcam_index in range(3):
                if webcam_index not in candidates:
                    candidates.append(webcam_index)
        elif source in (None, "", "webcam", "camera"):
            candidates = [0, 1, 2]

        return candidates

    def open_video_source(self, camera_id, source):
        """Open a configured source, falling back to local webcams if needed."""
        for candidate in self.build_source_candidates(source):
            cap = cv2.VideoCapture(candidate)
            if cap.isOpened():
                print(f"Opened source for {camera_id}: {candidate}")
                return cap, candidate
            cap.release()

        print(f"Error: Cannot open camera {camera_id} at {source}")
        print("Tried webcam fallbacks: 0, 1, 2")
        return None, None
    
    def calculate_area_from_frame(self, frame, known_width_meters=None, known_height_meters=None):
        """
        Calculate approximate area visible in frame
        Requires camera calibration or known dimensions
        """
        if known_width_meters and known_height_meters:
            return known_width_meters * known_height_meters
        
        # Default estimation based on typical camera field of view
        # This should be calibrated for each specific camera
        frame_height, frame_width = frame.shape[:2]
        estimated_area = 50  # Default to 50 sq meters
        return estimated_area
    
    # COCO skeleton connections: pairs of keypoint indices to draw as lines
    SKELETON = [
        (0, 1), (0, 2),           # nose → eyes
        (1, 3), (2, 4),           # eyes → ears
        (5, 6),                    # shoulder — shoulder
        (5, 7), (7, 9),           # left arm
        (6, 8), (8, 10),          # right arm
        (5, 11), (6, 12),         # shoulders → hips
        (11, 12),                  # hip — hip
        (11, 13), (13, 15),       # left leg
        (12, 14), (14, 16),       # right leg
    ]

    def detect_persons(self, frame):
        """Detect persons using YOLOv8 pose — validated by body keypoints."""
        frame_h, frame_w = frame.shape[:2]
        results = self.model(frame, classes=0, verbose=False)

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            boxes     = result.boxes
            keypoints = result.keypoints  # may be None for non-pose models

            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())

                # ── Confidence gate ──────────────────────────────────────────
                if confidence < self.conf_threshold:
                    continue

                # ── Geometric validation (coarse) ────────────────────────────
                if not self._is_valid_person(x1, y1, x2, y2, frame_w, frame_h):
                    continue

                # ── Body-structure validation via pose keypoints ─────────────
                # A t-shirt / bag has no human skeleton → fails this check.
                kps_xy   = None
                kps_conf = None
                if keypoints is not None and i < len(keypoints):
                    kp = keypoints[i]
                    kps_xy   = kp.xy[0].cpu().numpy()    # (17, 2)
                    kps_conf = kp.conf[0].cpu().numpy()  # (17,)

                    # Require enough total visible keypoints
                    visible = int((kps_conf > 0.3).sum())
                    if visible < self.min_valid_keypoints:
                        continue  # not enough body points → not a real person

                    # Require at least one shoulder to be clearly visible.
                    # Clothes/mannequins rarely have genuine shoulder keypoints.
                    ls, rs = self._shoulder_indices
                    if kps_conf[ls] < 0.5 and kps_conf[rs] < 0.5:
                        continue  # no shoulder detected → not a real person (bags/objects fail here)

                detections.append({
                    'bbox':       [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': confidence,
                    'kps_xy':     kps_xy,
                    'kps_conf':   kps_conf,
                })

        return detections

    def _is_valid_person(self, x1, y1, x2, y2, frame_w, frame_h):
        """
        Reject detections that are geometrically inconsistent with a human
        being, while remaining permissive enough for close-range webcam footage.

        Rules
        -----
        1. Minimum height  : box must be ≥ 50 px tall.
           (Reduced from 80 px to handle seated/partial people in webcam view.)

        2. Aspect ratio    : height/width must be in [0.5, 6.0].
           Lowered from 1.0 → 0.5 to handle persons sitting very close to the
           camera, who appear wider than tall due to foreshortening. Still
           rejects flat objects like t-shirts on hangers (very low ratio).

        3. Minimum area    : bounding-box area must be ≥ 1 500 px².
           Reduced from 3 000 px² to include smaller/distant persons.

        4. Frame-edge clip : if > 70 % of the box lies outside the frame,
           it is almost certainly a partial-frame artefact, not a person.
        """
        box_w  = x2 - x1
        box_h  = y2 - y1

        # 1. Minimum height
        if box_h < 50:
            return False

        # 2. Aspect ratio (height / width)
        if box_w == 0:
            return False
        aspect = box_h / box_w
        if not (0.5 <= aspect <= 6.0):
            return False

        # 3. Minimum area
        if box_w * box_h < 1500:
            return False

        # 4. Frame-edge clip — compute intersection area with frame
        ix1 = max(x1, 0)
        iy1 = max(y1, 0)
        ix2 = min(x2, frame_w)
        iy2 = min(y2, frame_h)
        intersection_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        box_area          = box_w * box_h
        if box_area == 0:
            return False
        inside_ratio = intersection_area / box_area
        if inside_ratio < 0.30:   # > 70 % outside → reject
            return False

        return True
    
    def calculate_density(self, person_count, area_sq_meters):
        """Calculate crowd density (persons per square meter)"""
        if area_sq_meters == 0:
            return 0
        return person_count / area_sq_meters
    
    def check_alert_conditions(self, camera_id, person_count, area_sq_meters):
        """Check if alert conditions are met"""
        safe_capacity = self.safe_capacity.get(camera_id, self.safe_capacity.get('default', 120))
        
        capacity_percentage = person_count / safe_capacity
        density = self.calculate_density(person_count, area_sq_meters)
        
        alert_level = None
        if capacity_percentage >= self.critical_threshold:
            alert_level = 'CRITICAL'
        elif capacity_percentage >= self.alert_threshold:
            alert_level = 'WARNING'
        
        return {
            'alert_level': alert_level,
            'person_count': person_count,
            'safe_capacity': safe_capacity,
            'capacity_percentage': capacity_percentage * 100,
            'density': density,
            'area_sq_meters': area_sq_meters
        }
    
    def should_send_alert(self, camera_id, alert_level):
        """Check if enough time has passed since last alert"""
        current_time = time.time()
        last_alert_time = self.alert_cooldown.get(f"{camera_id}_{alert_level}", 0)
        
        if current_time - last_alert_time > self.alert_cooldown_seconds:
            self.alert_cooldown[f"{camera_id}_{alert_level}"] = current_time
            return True
        return False
    
    def send_alert(self, camera_id, alert_data):
        """Send alert to authorities"""
        alert_level = alert_data['alert_level']
        
        if not self.should_send_alert(camera_id, alert_level):
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        alert_message = f"""
        CROWD CONTROL ALERT - {alert_level}
        
        Location: {camera_id}
        Timestamp: {timestamp}
        
        Current Count: {alert_data['person_count']} persons
        Safe Capacity: {alert_data['safe_capacity']} persons
        Capacity: {alert_data['capacity_percentage']:.1f}%
        Area: {alert_data['area_sq_meters']} sq meters
        Density: {alert_data['density']:.2f} persons/sq meter
        
        {self.get_alert_message(alert_level)}
        """
        
        print(f"\n{'='*60}")
        print(alert_message)
        print(f"{'='*60}\n")
        
        # Log to file
        self.log_alert(camera_id, alert_data, timestamp)
        
        # Send email/SMS (implement based on requirements)
        # self.send_email_alert(alert_message)
        # self.send_sms_alert(alert_message)
    
    def get_alert_message(self, alert_level):
        """Get appropriate alert message based on level"""
        if alert_level == 'CRITICAL':
            return "⚠️ CRITICAL: Capacity exceeded! Immediate action required to prevent stampede."
        elif alert_level == 'WARNING':
            return "⚠️ WARNING: Approaching capacity. Monitor closely and prepare crowd control measures."
        return ""
    
    def log_alert(self, camera_id, alert_data, timestamp):
        """Log alert to file"""
        log_entry = {
            'timestamp': timestamp,
            'camera_id': camera_id,
            'alert_data': alert_data
        }
        
        with open('crowd_alerts.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def draw_detections(self, frame, detections, alert_data):
        """Draw skeleton / keypoints instead of bounding boxes."""
        # ── alert-level colour ────────────────────────────────────────────────
        if alert_data['alert_level'] == 'CRITICAL':
            skel_color = (0, 0, 255)      # red
            dot_color  = (0, 80, 255)
        elif alert_data['alert_level'] == 'WARNING':
            skel_color = (0, 165, 255)   # orange
            dot_color  = (0, 120, 255)
        else:
            skel_color = (0, 230, 0)     # green
            dot_color  = (0, 255, 120)

        for detection in detections:
            kps_xy   = detection.get('kps_xy')
            kps_conf = detection.get('kps_conf')

            if kps_xy is not None and kps_conf is not None:
                # ── Draw skeleton limbs ───────────────────────────────────────
                for (a, b) in self.SKELETON:
                    if kps_conf[a] > 0.3 and kps_conf[b] > 0.3:
                        pt1 = (int(kps_xy[a][0]), int(kps_xy[a][1]))
                        pt2 = (int(kps_xy[b][0]), int(kps_xy[b][1]))
                        if pt1 != (0, 0) and pt2 != (0, 0):
                            cv2.line(frame, pt1, pt2, skel_color, 2, cv2.LINE_AA)

                # ── Draw keypoint dots ────────────────────────────────────────
                for j, (x, y) in enumerate(kps_xy):
                    if kps_conf[j] > 0.3 and (x, y) != (0, 0):
                        cv2.circle(frame, (int(x), int(y)), 4, dot_color, -1, cv2.LINE_AA)
            else:
                # Fallback: plain box if pose data unavailable
                x1, y1, x2, y2 = detection['bbox']
                cv2.rectangle(frame, (x1, y1), (x2, y2), skel_color, 2)

            # Confidence label near top of bounding box
            x1, y1 = detection['bbox'][0], detection['bbox'][1]
            cv2.putText(frame, f"{detection['confidence']:.2f}",
                        (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, dot_color, 1, cv2.LINE_AA)
        
        # Draw information panel
        self.draw_info_panel(frame, alert_data)
        
        return frame
    
    def draw_info_panel(self, frame, alert_data):
        """Draw HUD panel + full-width STAMPEDE / DANGER alert banner."""
        height, width = frame.shape[:2]
        alert_level   = alert_data['alert_level']

        # ── colour palette ────────────────────────────────────────────────────
        if alert_level == 'CRITICAL':
            text_color   = (0, 0, 255)      # red
            panel_color  = (0, 0, 80)       # dark red background
        elif alert_level == 'WARNING':
            text_color   = (0, 165, 255)    # orange
            panel_color  = (0, 50, 100)     # dark orange background
        else:
            text_color   = (0, 220, 0)      # green
            panel_color  = (0, 0, 0)        # black background

        # ── top info panel (semi-transparent) ────────────────────────────────
        panel_h = 160
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, panel_h), panel_color, -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        y = 30
        cv2.putText(frame, f"Person Count : {alert_data['person_count']}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 30
        cv2.putText(frame, f"Safe Capacity: {alert_data['safe_capacity']}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 30
        cv2.putText(frame, f"Capacity     : {alert_data['capacity_percentage']:.1f}%",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        y += 30
        cv2.putText(frame, f"Density      : {alert_data['density']:.2f} p/sqm",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 30
        cv2.putText(frame, f"Status       : {alert_level or 'NORMAL'}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)

        # ── full-width alert banner at bottom of frame ────────────────────────
        if alert_level == 'CRITICAL':
            # Flashing red banner — blink every ~0.6 s using wall clock
            if int(time.time() * 1.7) % 2 == 0:
                banner_h = 70
                bx1, by1 = 0, height - banner_h
                bx2, by2 = width, height
                ov2 = frame.copy()
                cv2.rectangle(ov2, (bx1, by1), (bx2, by2), (0, 0, 200), -1)
                cv2.addWeighted(ov2, 0.80, frame, 0.20, 0, frame)
                banner_text = "!! DANGER ALERT !!  CROWD CAPACITY EXCEEDED"
                (tw, th), _ = cv2.getTextSize(
                    banner_text, cv2.FONT_HERSHEY_DUPLEX, 0.85, 2)
                tx = max(0, (width - tw) // 2)
                ty = by1 + th + 10
                # Shadow for readability
                cv2.putText(frame, banner_text, (tx + 2, ty + 2),
                            cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 0), 3)
                cv2.putText(frame, banner_text, (tx, ty),
                            cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)

        elif alert_level == 'WARNING':
            banner_h = 60
            bx1, by1 = 0, height - banner_h
            bx2, by2 = width, height
            ov2 = frame.copy()
            cv2.rectangle(ov2, (bx1, by1), (bx2, by2), (0, 100, 200), -1)
            cv2.addWeighted(ov2, 0.75, frame, 0.25, 0, frame)
            banner_text = "⚠  STAMPEDE ALERT  —  Approaching Safety Limit"
            (tw, th), _ = cv2.getTextSize(
                banner_text, cv2.FONT_HERSHEY_DUPLEX, 0.80, 2)
            tx = max(0, (width - tw) // 2)
            ty = by1 + th + 8
            cv2.putText(frame, banner_text, (tx + 2, ty + 2),
                        cv2.FONT_HERSHEY_DUPLEX, 0.80, (0, 0, 0), 3)
            cv2.putText(frame, banner_text, (tx, ty),
                        cv2.FONT_HERSHEY_DUPLEX, 0.80, (255, 255, 255), 2)
    
    def process_camera_feed(self, camera_id, source):
        """Process video feed from a camera"""
        cap, resolved_source = self.open_video_source(camera_id, source)
        if cap is None:
            return
        
        area_sq_meters = self.area_dimensions.get(camera_id, 
                                                  self.area_dimensions.get('default', 50))
        
        print(f"Processing camera {camera_id}...")
        print(f"Using source: {resolved_source}")
        print(f"Area: {area_sq_meters} sq meters")
        print(f"Safe capacity: {self.safe_capacity.get(camera_id, self.safe_capacity.get('default', 120))} persons")
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                print(f"Error reading frame from {camera_id}")
                break

            # Detect persons
            detections = self.detect_persons(frame)
            person_count = len(detections)

            # Check alert conditions
            alert_data = self.check_alert_conditions(camera_id, person_count, area_sq_meters)

            # ── CSV: log person count every 10 seconds ────────────────────────
            self.log_person_count_csv(camera_id, alert_data)

            # Send alert if necessary
            if alert_data['alert_level']:
                self.send_alert(camera_id, alert_data)

            # Draw detections and info
            annotated_frame = self.draw_detections(frame, detections, alert_data)

            # Display frame
            cv2.imshow(f'Crowd Control - {camera_id}', annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_running = False
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def start_monitoring(self):
        """Start monitoring all configured cameras"""
        self.is_running = True
        threads = []
        
        if not self.camera_sources:
            print("No camera sources configured. Using default webcam.")
            self.camera_sources = {'webcam': 0}
        
        for camera_id, source in self.camera_sources.items():
            thread = threading.Thread(target=self.process_camera_feed, 
                                     args=(camera_id, source))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads
        for thread in threads:
            thread.join()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False


def main():
    """Main function to run the crowd control system"""
    print("="*60)
    print("CROWD CONTROL SYSTEM")
    print("Real-time Person Detection and Density Monitoring")
    print("="*60)
    print("\nInitializing system...")
    
    # Initialize system
    system = CrowdControlSystem('config.json')
    
    print("\nStarting monitoring...")
    print("Press 'q' in any video window to stop")
    
    try:
        system.start_monitoring()
    except KeyboardInterrupt:
        print("\nStopping system...")
        system.stop_monitoring()
    
    print("System stopped.")


if __name__ == "__main__":
    main()
