# Project Structure - Crowd Control System

## 📁 Directory Structure

```
crowd-control-system/
│
├── crowd_control.py              # Main application file
├── advanced_crowd_control.py     # Advanced features (heatmap, zones)
├── test_system.py                # Testing and validation script
├── demo.py                       # Interactive demo without real cameras
│
├── config.json                   # Main configuration file
├── requirements.txt              # Python dependencies
│
├── README.md                     # Project documentation
├── DEPLOYMENT.md                 # Production deployment guide
├── PROJECT_STRUCTURE.md          # This file
│
├── models/                       # Directory for AI models
│   └── yolov8n.pt               # YOLOv8 nano model (auto-downloaded)
│
├── logs/                         # Log files directory
│   ├── crowd_alerts.log         # Alert history
│   ├── system.log               # System operations log
│   └── error.log                # Error logs
│
├── recordings/                   # Video recordings (optional)
│   └── YYYY-MM-DD/              # Organized by date
│       └── camera_id_timestamp.mp4
│
├── snapshots/                    # Alert snapshots
│   └── YYYY-MM-DD/
│       └── alert_timestamp.jpg
│
├── analytics/                    # Analytics and reports
│   ├── daily_reports/
│   ├── weekly_reports/
│   └── monthly_reports/
│
└── utils/                        # Utility modules (optional)
    ├── __init__.py
    ├── alert_system.py          # Alert management
    ├── camera_manager.py        # Camera handling
    ├── database.py              # Data persistence
    └── visualization.py         # Visualization utilities
```

---

## 📄 File Descriptions

### Core Application Files

#### `crowd_control.py`
**Purpose:** Main application entry point
**Key Features:**
- Real-time person detection using YOLOv8
- Multi-camera support with threading
- Automatic alert generation
- Configurable capacity monitoring
- Live video display with annotations

**Main Classes:**
- `CrowdControlSystem`: Core system class handling all operations

**Usage:**
```bash
python crowd_control.py
```

---

#### `advanced_crowd_control.py`
**Purpose:** Extended functionality for advanced monitoring
**Key Features:**
- Density heatmap visualization
- Zone-based crowd monitoring
- Crowd flow analysis
- Advanced analytics dashboard
- Person tracking across frames

**Main Classes:**
- `AdvancedCrowdControl`: Extended system with advanced features

**Usage:**
```bash
python advanced_crowd_control.py
```

---

#### `test_system.py`
**Purpose:** System testing and validation
**Key Features:**
- Component testing
- Camera connectivity verification
- Model download verification
- Detection accuracy testing
- Configuration validation

**Usage:**
```bash
python test_system.py
```

---

#### `demo.py`
**Purpose:** Interactive demonstration without real cameras
**Key Features:**
- Simulated crowd scenarios
- Visual representation of monitoring
- Different alert level demonstrations
- No camera requirement for testing

**Usage:**
```bash
python demo.py
```

---

### Configuration Files

#### `config.json`
**Purpose:** System configuration
**Contains:**
- Camera source URLs/IDs
- Area dimensions (sq meters)
- Safe capacity thresholds
- Alert recipients
- Email/SMS settings
- Detection parameters
- Zone definitions

**Example Structure:**
```json
{
  "camera_sources": { ... },
  "area_dimensions": { ... },
  "safe_capacity": { ... },
  "alert_threshold": 0.85,
  "alert_recipients": [ ... ]
}
```

---

#### `requirements.txt`
**Purpose:** Python package dependencies
**Key Packages:**
- opencv-python: Video processing
- ultralytics: YOLOv8 model
- numpy: Numerical operations
- torch: Deep learning framework

**Installation:**
```bash
pip install -r requirements.txt
```

---

### Documentation Files

#### `README.md`
**Purpose:** Main project documentation
**Sections:**
- Project overview
- Features
- Installation guide
- Usage instructions
- Configuration help
- Troubleshooting

---

#### `DEPLOYMENT.md`
**Purpose:** Production deployment guide
**Sections:**
- Pre-deployment checklist
- Step-by-step deployment
- System configuration
- Monitoring setup
- Security considerations
- Performance optimization

---

## 🔧 Component Architecture

### 1. Detection Module
```
Input: Video Frame
  ↓
YOLOv8 Detection
  ↓
Person Bounding Boxes
  ↓
Count & Tracking
  ↓
Output: Person Count
```

### 2. Analysis Module
```
Person Count + Area Dimensions
  ↓
Density Calculation
  ↓
Capacity Comparison
  ↓
Alert Level Determination
  ↓
Output: Alert Status
```

### 3. Alert Module
```
Alert Triggered
  ↓
Check Cooldown
  ↓
Generate Alert Message
  ↓
Send Notifications (Email/SMS/Log)
  ↓
Log to Database
```

### 4. Visualization Module
```
Frame + Detections + Alerts
  ↓
Draw Bounding Boxes
  ↓
Add Information Panel
  ↓
Apply Heatmap (Advanced)
  ↓
Display/Record
```

---

## 🔄 Data Flow

```
CCTV Cameras
     ↓
Video Streams (RTSP/USB)
     ↓
Frame Capture
     ↓
Person Detection (YOLOv8)
     ↓
Crowd Analysis
     ↓
┌────────────┬────────────┐
│            │            │
Alert System  Logging    Display
     ↓            ↓           ↓
Authorities   Database   Monitor
```

---

## 🗄️ Data Storage

### Logs Format

#### `crowd_alerts.log`
```json
{
  "timestamp": "2026-01-28 14:30:00",
  "camera_id": "platform_1",
  "alert_level": "CRITICAL",
  "person_count": 135,
  "safe_capacity": 120,
  "capacity_percentage": 112.5,
  "density": 2.7
}
```

#### `system.log`
```
2026-01-28 14:30:00 [INFO] System started
2026-01-28 14:30:05 [INFO] Camera platform_1 connected
2026-01-28 14:30:10 [INFO] Detection started
2026-01-28 14:35:00 [WARNING] High crowd detected
```

---

## 🔌 Integration Points

### 1. Camera Integration
- **RTSP streams** for IP cameras
- **USB cameras** for local testing
- **Video files** for analysis

### 2. Alert Integration
- **Email** via SMTP
- **SMS** via Twilio/AWS SNS
- **Push notifications** via mobile app
- **REST API** for custom integrations

### 3. Database Integration
- **SQLite** for local storage
- **PostgreSQL/MySQL** for production
- **MongoDB** for analytics

### 4. External Systems
- **Access Control** systems
- **Public Announcement** systems
- **Emergency Response** platforms
- **Analytics Dashboards**

---

## 🚀 Scalability

### Horizontal Scaling
```
Load Balancer
     ↓
┌──────┬──────┬──────┐
│      │      │      │
Server1 Server2 Server3
│      │      │      │
Cameras Cameras Cameras
    ↓       ↓       ↓
  Central Database
```

### Vertical Scaling
- Add more RAM for caching
- Upgrade to faster GPU
- Increase storage capacity
- Better network bandwidth

---

## 📊 Performance Metrics

### Target Specifications
- **Detection Rate:** 15-30 FPS per camera
- **Accuracy:** >95% for person detection
- **Latency:** <500ms from detection to alert
- **Concurrent Cameras:** 10+ per server
- **Uptime:** 99.9%

### Resource Usage
- **CPU:** 30-50% per camera (without GPU)
- **GPU:** 20-40% for 4 cameras
- **RAM:** 2-4GB base + 500MB per camera
- **Network:** 5-10 Mbps per camera
- **Storage:** ~100MB/hour per camera (logs only)

---

## 🔐 Security Architecture

```
┌─────────────────────────────────────┐
│          Firewall                   │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│          VPN Gateway                │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│    Application Layer (Auth)         │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│    Crowd Control System             │
└─────────────────────────────────────┘
```

---

## 🧪 Testing Strategy

### Unit Tests
- Detection accuracy
- Alert logic
- Configuration parsing
- Camera connectivity

### Integration Tests
- End-to-end flow
- Multi-camera coordination
- Alert delivery
- Database operations

### Performance Tests
- Load testing
- Stress testing
- Latency measurement
- Resource monitoring

---

## 📈 Future Enhancements

### Phase 2
- [ ] Mobile application
- [ ] Web dashboard
- [ ] Machine learning for flow prediction
- [ ] Historical data analytics

### Phase 3
- [ ] Facial recognition integration
- [ ] Behavior analysis
- [ ] Predictive alerts
- [ ] Multi-site central monitoring

---

## 🛠️ Development Workflow

```
1. Development
   └─> Local Testing (test_system.py)
       └─> Demo Validation (demo.py)
           └─> Integration Testing
               └─> Staging Deployment
                   └─> Production Deployment
```

---

## 📞 Support & Maintenance

### Regular Tasks
- **Daily:** Log review, system health check
- **Weekly:** Performance analysis, alert review
- **Monthly:** Model retraining, capacity review
- **Quarterly:** System audit, security updates

---

**Document Version:** 1.0  
**Last Updated:** January 28, 2026  
**Maintainer:** Project Team
