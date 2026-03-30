# Deployment Guide - Crowd Control System

## 🚀 Production Deployment Guide

This guide will help you deploy the Crowd Control System in a production environment such as a railway station, stadium, or public venue.

---

## 📋 Pre-Deployment Checklist

### 1. Hardware Setup
- [ ] CCTV cameras installed and operational
- [ ] Network connectivity verified for all cameras
- [ ] Server/Computer with sufficient processing power
- [ ] GPU available for optimal performance (recommended)
- [ ] UPS/Backup power supply configured
- [ ] Storage for video recordings and logs

### 2. Network Configuration
- [ ] Static IP addresses assigned to all cameras
- [ ] RTSP stream URLs documented
- [ ] Firewall rules configured
- [ ] VPN access for remote monitoring (if needed)
- [ ] Bandwidth sufficient for all camera streams

### 3. Software Requirements
- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] YOLOv8 model downloaded
- [ ] GPU drivers and CUDA installed (if using GPU)

---

## 🔧 Step-by-Step Deployment

### Step 1: Site Survey

#### Camera Placement
```
Optimal camera placement for crowd monitoring:
- Height: 3-5 meters above ground
- Angle: 30-45 degrees downward
- Coverage: Overlapping fields of view
- Lighting: Adequate illumination or IR capability
```

#### Area Calibration
For each monitoring area, measure:
1. Physical dimensions (length × width in meters)
2. Camera field of view coverage
3. Typical crowd patterns
4. Entry/exit points

### Step 2: Camera Configuration

Create a camera mapping document:

```json
{
  "camera_id": "platform_1_east",
  "location": "Platform 1 - East End",
  "rtsp_url": "rtsp://192.168.1.101:554/stream1",
  "area_sq_meters": 150,
  "safe_capacity": 300,
  "coordinates": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "zones": [
    {
      "name": "waiting_area",
      "capacity": 150,
      "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]]
    }
  ]
}
```

### Step 3: System Configuration

Edit `config.json` with production settings:

```json
{
  "camera_sources": {
    "platform_1_east": "rtsp://192.168.1.101:554/stream1",
    "platform_1_west": "rtsp://192.168.1.102:554/stream1",
    "entrance_main": "rtsp://192.168.1.103:554/stream1"
  },
  
  "area_dimensions": {
    "platform_1_east": 150,
    "platform_1_west": 150,
    "entrance_main": 80
  },
  
  "safe_capacity": {
    "platform_1_east": 300,
    "platform_1_west": 300,
    "entrance_main": 160
  },
  
  "alert_threshold": 0.85,
  "critical_threshold": 1.0,
  "alert_cooldown_seconds": 300,
  
  "alert_recipients": [
    {
      "name": "Control Room",
      "email": "control@station.gov.in",
      "phone": "+91-1234567890",
      "priority": "high"
    },
    {
      "name": "Station Manager",
      "email": "manager@station.gov.in",
      "phone": "+91-0987654321",
      "priority": "high"
    },
    {
      "name": "Security Officer",
      "email": "security@station.gov.in",
      "phone": "+91-1122334455",
      "priority": "medium"
    }
  ]
}
```

### Step 4: Alert System Configuration

#### Email Alerts
```python
# In config.json
"email_config": {
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "alerts@crowdcontrol.system",
  "sender_password": "your_app_password",
  "use_tls": true
}
```

#### SMS Alerts (Optional)
Integrate with SMS gateway:
```python
# Example using Twilio
"sms_config": {
  "provider": "twilio",
  "account_sid": "YOUR_ACCOUNT_SID",
  "auth_token": "YOUR_AUTH_TOKEN",
  "from_number": "+1234567890"
}
```

### Step 5: Testing Phase

#### Unit Testing
```bash
# Test individual components
python test_system.py

# Test camera connectivity
python -c "import cv2; cap = cv2.VideoCapture('rtsp://camera_url'); print('OK' if cap.isOpened() else 'FAIL')"

# Test detection accuracy
python test_detection.py --camera platform_1_east --duration 300
```

#### Integration Testing
```bash
# Run system with all cameras for 1 hour
python crowd_control.py --test-mode --duration 3600

# Verify alerts are received
# Check logs: tail -f crowd_alerts.log
```

### Step 6: Production Deployment

#### Option A: Screen/Tmux (Simple)
```bash
# Start in a screen session
screen -S crowd_control
python crowd_control.py
# Detach: Ctrl+A, then D
```

#### Option B: Systemd Service (Recommended)

Create `/etc/systemd/system/crowd-control.service`:
```ini
[Unit]
Description=Crowd Control Monitoring System
After=network.target

[Service]
Type=simple
User=crowdcontrol
WorkingDirectory=/opt/crowd-control
ExecStart=/opt/crowd-control/venv/bin/python /opt/crowd-control/crowd_control.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/crowd-control/output.log
StandardError=append:/var/log/crowd-control/error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable crowd-control
sudo systemctl start crowd-control
sudo systemctl status crowd-control
```

#### Option C: Docker (Advanced)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "crowd_control.py"]
```

Build and run:
```bash
docker build -t crowd-control:latest .
docker run -d --name crowd-control \
  --restart unless-stopped \
  -v /opt/crowd-control/config.json:/app/config.json \
  -v /opt/crowd-control/logs:/app/logs \
  crowd-control:latest
```

---

## 📊 Monitoring & Maintenance

### System Health Monitoring

Create a monitoring script:
```bash
#!/bin/bash
# /opt/crowd-control/monitor.sh

# Check if process is running
if ! pgrep -f "crowd_control.py" > /dev/null; then
    echo "Crowd Control System is DOWN!"
    systemctl restart crowd-control
    # Send alert to admin
fi

# Check disk space
DISK_USAGE=$(df -h /var/log | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk space warning: ${DISK_USAGE}%"
fi

# Check log file size
LOG_SIZE=$(du -m /var/log/crowd-control/output.log | cut -f1)
if [ $LOG_SIZE -gt 1000 ]; then
    echo "Log file too large, rotating..."
    logrotate /etc/logrotate.d/crowd-control
fi
```

Add to crontab:
```bash
*/5 * * * * /opt/crowd-control/monitor.sh
```

### Log Rotation

Create `/etc/logrotate.d/crowd-control`:
```
/var/log/crowd-control/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 crowdcontrol crowdcontrol
    sharedscripts
    postrotate
        systemctl reload crowd-control
    endscript
}
```

---

## 🔒 Security Considerations

### 1. Network Security
- Use VPN for remote access
- Implement firewall rules
- Secure RTSP streams with authentication
- Use HTTPS for web interface

### 2. Data Privacy
- Implement face blurring if required by regulations
- Secure storage of video recordings
- Regular data purging based on retention policy
- Access control for logs and recordings

### 3. Physical Security
- Secure server room access
- Camera tampering detection
- Backup power supply
- Redundant network connections

---

## 📈 Performance Optimization

### GPU Acceleration
```python
# Force CUDA
import torch
torch.cuda.is_available()  # Should return True

# In config
"detection_settings": {
    "device": "cuda:0",  # or "cpu"
    "fp16": true  # Half precision for faster inference
}
```

### Multi-threading
```python
# Process multiple cameras in parallel
"processing": {
    "max_workers": 4,  # Number of parallel threads
    "frame_skip": 2    # Process every Nth frame
}
```

### Frame Rate Optimization
```python
# Reduce resolution for faster processing
"video_settings": {
    "resize_width": 1280,
    "resize_height": 720,
    "target_fps": 15
}
```

---

## 🆘 Troubleshooting

### Common Issues

#### 1. Camera Connection Failed
```bash
# Test RTSP stream
ffmpeg -i rtsp://camera_ip/stream -frames:v 1 test.jpg

# Check network
ping camera_ip
```

#### 2. High CPU Usage
- Enable GPU acceleration
- Reduce frame rate
- Use smaller YOLO model (yolov8n)
- Process fewer cameras per server

#### 3. False Detections
- Increase confidence threshold
- Fine-tune model on site-specific data
- Adjust lighting conditions

#### 4. Missed Detections
- Improve camera angles
- Enhance lighting
- Use larger YOLO model (yolov8m/l)

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Daily:**
- Check system status
- Review alert logs
- Verify camera feeds

**Weekly:**
- Review detection accuracy
- Check disk space
- Update alert contact list

**Monthly:**
- System backup
- Model performance evaluation
- Security patches

**Quarterly:**
- System calibration
- Capacity threshold review
- Performance optimization

---

## 📚 Additional Resources

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [OpenCV Camera Calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)
- [RTSP Streaming Guide](https://github.com/aler9/rtsp-simple-server)

---

## 📝 Deployment Checklist

```
Pre-Deployment:
□ Hardware installed and tested
□ Network configured
□ Software installed
□ Configuration customized
□ Testing completed

Deployment:
□ System running in production
□ Monitoring configured
□ Alerts tested
□ Logs verified
□ Documentation completed

Post-Deployment:
□ Training provided to operators
□ Emergency procedures documented
□ Contact list distributed
□ First week monitoring
□ Performance baseline established
```

---

**For support: support@crowdcontrol.system**
