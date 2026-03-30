# Crowd Control System 🚨

A real-time AI-powered crowd monitoring system that uses computer vision to detect persons in CCTV footage, analyze crowd density, and alert authorities before dangerous situations like stampedes occur.

## 🎯 Features

### Core Features
- **Real-time Person Detection** using YOLOv8
- **Automatic Crowd Counting** with high accuracy
- **Area-based Density Analysis** (persons per square meter)
- **Multi-level Alert System** (Warning & Critical)
- **Multi-camera Support** with parallel processing
- **Configurable Capacity Thresholds** for different locations

### Advanced Features
- **Density Heatmap Visualization** showing crowd concentration
- **Zone-based Monitoring** for specific areas (waiting areas, platforms, etc.)
- **Alert Cooldown System** to prevent alert spam
- **Comprehensive Logging** of all alerts and incidents
- **Real-time Dashboard** with statistics and analytics

## 🏗️ System Architecture

```
┌─────────────────┐
│   CCTV Cameras  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Video Feed Input   │
│  (RTSP/USB/File)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   YOLOv8 Detection  │
│  Person Detection   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Density Analysis   │
│  Count vs Capacity  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Alert System       │
│  Notify Authorities │
└─────────────────────┘
```

## 📋 Requirements

### Hardware Requirements
- **Minimum:**
  - CPU: Intel i5 or equivalent
  - RAM: 8GB
  - GPU: Optional (significantly improves performance)
  
- **Recommended:**
  - CPU: Intel i7/Ryzen 7 or better
  - RAM: 16GB
  - GPU: NVIDIA GTX 1060 or better (with CUDA support)

### Software Requirements
- Python 3.8 or higher
- OpenCV 4.x
- PyTorch (for YOLOv8)
- CUDA (optional, for GPU acceleration)

## 🚀 Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/crowd-control-system.git
cd crowd-control-system
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Download YOLOv8 Model
The model will be automatically downloaded on first run, or you can manually download:
```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

## ⚙️ Configuration

Edit `config.json` to customize your setup:

### 1. Camera Sources
```json
"camera_sources": {
  "railway_station_platform1": "rtsp://192.168.1.100/stream",
  "entrance_gate": 0,  // 0 for default webcam
  "test_video": "crowd_video.mp4"
}
```

### 2. Area Dimensions (in square meters)
```json
"area_dimensions": {
  "railway_station_platform1": 150,
  "entrance_gate": 50
}
```

### 3. Safe Capacity (maximum persons)
```json
"safe_capacity": {
  "railway_station_platform1": 300,
  "entrance_gate": 100
}
```

### 4. Alert Thresholds
```json
"alert_threshold": 0.85,      // Warning at 85% capacity
"critical_threshold": 1.0,    // Critical at 100% capacity
"alert_cooldown_seconds": 300 // Wait 5 min between alerts
```

### 5. Alert Recipients
```json
"alert_recipients": [
  {
    "name": "Control Room",
    "email": "control@railway.gov.in",
    "phone": "+91-XXXXXXXXXX"
  }
]
```

## 🎮 Usage

### Basic Usage
```bash
python crowd_control.py
```

### Advanced Features
```bash
python advanced_crowd_control.py
```

### Command Line Options
```bash
# Use specific config file
python crowd_control.py --config custom_config.json

# Process specific video file
python crowd_control.py --video crowd_footage.mp4

# Use specific camera
python crowd_control.py --camera 0

# Enable debug mode
python crowd_control.py --debug
```

## 📊 Understanding the Output

### Display Information
The system shows a real-time video feed with:

1. **Bounding Boxes**: Green/Orange/Red boxes around detected persons
2. **Information Panel**: 
   - Current person count
   - Safe capacity
   - Capacity percentage
   - Density (persons/sq meter)
   - Alert status

### Alert Levels

| Level | Condition | Color | Action |
|-------|-----------|-------|--------|
| **NORMAL** | < 85% capacity | Green | Monitor normally |
| **WARNING** | 85-99% capacity | Orange | Increase monitoring, prepare crowd control |
| **CRITICAL** | ≥ 100% capacity | Red | Immediate action required, stop entry |

## 🔧 Customization

### Adjusting Detection Sensitivity
In the code, modify:
```python
confidence_threshold = 0.4  # Lower = more detections, higher false positives
```

### Changing Alert Timing
```python
alert_cooldown_seconds = 300  # Time between repeat alerts
```

### Adding Custom Zones
```json
"density_zones": {
  "camera_id": [
    {
      "name": "waiting_area",
      "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
      "capacity": 150
    }
  ]
}
```

## 📈 Advanced Features

### Heatmap Visualization
Shows areas of high crowd concentration:
```python
system = AdvancedCrowdControl('config.json')
frame_with_heatmap, count, heatmap = system.process_frame_advanced(frame, camera_id)
```

### Zone-based Monitoring
Monitor specific areas within camera view:
```python
zones = [
    {"name": "platform", "polygon": [...], "capacity": 200},
    {"name": "entrance", "polygon": [...], "capacity": 50}
]
```

### Analytics Dashboard
Generate reports and visualizations:
```python
report = system.generate_analytics_report(camera_id, start_time, end_time)
```

## 🎯 Use Cases

### Railway Stations
- Monitor platforms during peak hours
- Prevent stampedes during train arrivals
- Manage crowd during festivals

### Stadiums & Events
- Concert crowd management
- Sports event monitoring
- Festival crowd control

### Shopping Malls
- Black Friday sale management
- Holiday season monitoring
- Emergency evacuation assistance

### Public Gatherings
- Religious gatherings
- Political rallies
- Public celebrations

## 🔒 Safety & Privacy

- **Data Privacy**: System processes video locally, no cloud storage
- **GDPR Compliant**: Can be configured for privacy regulations
- **Face Anonymization**: Optional feature to blur faces
- **Secure Alerts**: Encrypted communication for alert messages

## 📝 Logging

All alerts are logged to `crowd_alerts.log`:
```json
{
  "timestamp": "2026-01-28 14:30:00",
  "camera_id": "platform1",
  "alert_data": {
    "alert_level": "CRITICAL",
    "person_count": 320,
    "safe_capacity": 300,
    "capacity_percentage": 106.7
  }
}
```

## 🐛 Troubleshooting

### Camera Not Detected
```bash
# List available cameras
python -c "import cv2; print([cv2.VideoCapture(i).isOpened() for i in range(5)])"
```

### Low FPS / Performance Issues
- Use YOLOv8n (nano) instead of larger models
- Enable GPU acceleration
- Reduce video resolution
- Process every Nth frame instead of all frames

### False Detections
- Increase confidence threshold (0.4 → 0.6)
- Use YOLOv8m or YOLOv8l for better accuracy
- Fine-tune model on your specific environment

## 🚀 Future Enhancements

- [ ] Integration with access control systems
- [ ] Mobile app for alerts
- [ ] Crowd flow prediction using ML
- [ ] Automatic crowd dispersal suggestions
- [ ] Integration with public announcement systems
- [ ] Multi-camera person tracking
- [ ] Historical data analysis and reporting
- [ ] Integration with emergency response systems

## 📚 References

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Crowd Dynamics Research](https://www.sciencedirect.com/topics/engineering/crowd-dynamics)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

Your Name - Initial work

## 🙏 Acknowledgments

- Ultralytics for YOLOv8
- OpenCV community
- Research papers on crowd dynamics

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: support@crowdcontrol.system
- Documentation: [Wiki](link-to-wiki)

## ⚠️ Disclaimer

This system is designed to assist in crowd management but should not be the sole method for ensuring public safety. Always have trained personnel and proper safety protocols in place.

---

**Built with ❤️ for Public Safety**
