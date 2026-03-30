"""
Demo Script - Crowd Control System
Simulates different crowd scenarios for demonstration
"""

import cv2
import numpy as np
from datetime import datetime
import time

class CrowdDemo:
    def __init__(self):
        self.scenarios = {
            1: "Normal - Low Crowd",
            2: "Warning - High Crowd",
            3: "Critical - Overcrowded",
            4: "Custom Scenario"
        }
        
    def display_menu(self):
        """Display demo menu"""
        print("\n" + "="*60)
        print("CROWD CONTROL SYSTEM - DEMO MODE")
        print("="*60)
        print("\nSelect a scenario to simulate:")
        print()
        for key, value in self.scenarios.items():
            print(f"{key}. {value}")
        print("0. Exit")
        print()
        
    def simulate_crowd(self, scenario_type):
        """Simulate crowd based on scenario"""
        if scenario_type == 1:
            return self.normal_scenario()
        elif scenario_type == 2:
            return self.warning_scenario()
        elif scenario_type == 3:
            return self.critical_scenario()
        else:
            return self.custom_scenario()
    
    def normal_scenario(self):
        """Simulate normal crowd (30-50 people in 50 sq meters)"""
        print("\n📊 SCENARIO: Normal Crowd")
        print("   Area: 50 sq meters")
        print("   Capacity: 120 persons")
        print("   Current: 35-45 persons")
        print("   Status: NORMAL ✓")
        
        return {
            'person_count': np.random.randint(35, 46),
            'safe_capacity': 120,
            'area_sq_meters': 50,
            'status': 'NORMAL'
        }
    
    def warning_scenario(self):
        """Simulate warning level crowd (102-110 people in 50 sq meters)"""
        print("\n⚠️  SCENARIO: Warning Level")
        print("   Area: 50 sq meters")
        print("   Capacity: 120 persons")
        print("   Current: 102-110 persons")
        print("   Status: WARNING ⚠️")
        
        return {
            'person_count': np.random.randint(102, 111),
            'safe_capacity': 120,
            'area_sq_meters': 50,
            'status': 'WARNING'
        }
    
    def critical_scenario(self):
        """Simulate critical crowd (125-150 people in 50 sq meters)"""
        print("\n🚨 SCENARIO: Critical Overcrowding")
        print("   Area: 50 sq meters")
        print("   Capacity: 120 persons")
        print("   Current: 125-140 persons")
        print("   Status: CRITICAL 🚨")
        
        return {
            'person_count': np.random.randint(125, 141),
            'safe_capacity': 120,
            'area_sq_meters': 50,
            'status': 'CRITICAL'
        }
    
    def custom_scenario(self):
        """Allow user to input custom values"""
        print("\n🎯 SCENARIO: Custom")
        
        try:
            area = float(input("Enter area (sq meters): "))
            capacity = int(input("Enter safe capacity: "))
            count = int(input("Enter current person count: "))
            
            return {
                'person_count': count,
                'safe_capacity': capacity,
                'area_sq_meters': area,
                'status': 'CUSTOM'
            }
        except ValueError:
            print("Invalid input, using defaults")
            return self.normal_scenario()
    
    def create_visualization(self, data):
        """Create a visualization of the crowd scenario"""
        width, height = 800, 600
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background
        frame[:] = (40, 40, 40)
        
        # Calculate metrics
        capacity_percentage = (data['person_count'] / data['safe_capacity']) * 100
        density = data['person_count'] / data['area_sq_meters']
        
        # Determine colors based on status
        if capacity_percentage >= 100:
            status_color = (0, 0, 255)  # Red
            status_text = "CRITICAL"
        elif capacity_percentage >= 85:
            status_color = (0, 165, 255)  # Orange
            status_text = "WARNING"
        else:
            status_color = (0, 255, 0)  # Green
            status_text = "NORMAL"
        
        # Title
        cv2.putText(frame, "CROWD CONTROL MONITORING SYSTEM", 
                   (150, 50), cv2.FONT_HERSHEY_BOLD, 1, (255, 255, 255), 2)
        
        # Draw area representation
        area_x, area_y = 100, 150
        area_w, area_h = 600, 300
        cv2.rectangle(frame, (area_x, area_y), (area_x + area_w, area_y + area_h), 
                     (100, 100, 100), 2)
        cv2.putText(frame, f"Monitored Area: {data['area_sq_meters']} sq meters", 
                   (area_x, area_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Simulate person positions
        persons_to_show = min(data['person_count'], 100)  # Show max 100 for visualization
        for i in range(persons_to_show):
            x = np.random.randint(area_x + 20, area_x + area_w - 20)
            y = np.random.randint(area_y + 20, area_y + area_h - 20)
            cv2.circle(frame, (x, y), 8, status_color, -1)
            cv2.circle(frame, (x, y), 8, (255, 255, 255), 1)
        
        # Info panel
        info_y = 480
        cv2.rectangle(frame, (50, info_y), (750, 570), (20, 20, 20), -1)
        cv2.rectangle(frame, (50, info_y), (750, 570), (255, 255, 255), 2)
        
        # Display information
        info_items = [
            f"Person Count: {data['person_count']}",
            f"Safe Capacity: {data['safe_capacity']}",
            f"Capacity: {capacity_percentage:.1f}%",
            f"Density: {density:.2f} persons/sq meter",
            f"Status: {status_text}"
        ]
        
        for i, item in enumerate(info_items):
            y_pos = info_y + 25 + (i * 20)
            color = status_color if i == 4 else (255, 255, 255)
            cv2.putText(frame, item, (70, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (600, 590), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        return frame
    
    def run_demo(self):
        """Run the interactive demo"""
        while True:
            self.display_menu()
            
            try:
                choice = int(input("Enter your choice: "))
                
                if choice == 0:
                    print("\nExiting demo...")
                    break
                
                if choice not in range(1, 5):
                    print("Invalid choice, try again")
                    continue
                
                # Generate scenario data
                data = self.simulate_crowd(choice)
                
                # Create visualization
                frame = self.create_visualization(data)
                
                # Display
                cv2.imshow('Crowd Control Demo', frame)
                
                print("\nPress any key in the image window to continue...")
                print("Press 'q' to return to menu")
                
                key = cv2.waitKey(0)
                if key == ord('q'):
                    cv2.destroyAllWindows()
                    continue
                
            except ValueError:
                print("Invalid input, please enter a number")
            except KeyboardInterrupt:
                print("\nDemo interrupted")
                break
        
        cv2.destroyAllWindows()
    
    def generate_report(self, data):
        """Generate a text report of the scenario"""
        capacity_percentage = (data['person_count'] / data['safe_capacity']) * 100
        density = data['person_count'] / data['area_sq_meters']
        
        report = f"""
{'='*60}
CROWD CONTROL MONITORING REPORT
{'='*60}

Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

AREA INFORMATION:
  Area Size: {data['area_sq_meters']} square meters
  Safe Capacity: {data['safe_capacity']} persons

CURRENT STATUS:
  Person Count: {data['person_count']}
  Capacity Utilization: {capacity_percentage:.1f}%
  Crowd Density: {density:.2f} persons/sq meter

ALERT LEVEL: {data['status']}

RECOMMENDATIONS:
"""
        
        if capacity_percentage >= 100:
            report += """
  🚨 IMMEDIATE ACTION REQUIRED
  - Stop entry immediately
  - Initiate crowd dispersal procedures
  - Alert all security personnel
  - Activate emergency protocols
  - Monitor for stampede risks
"""
        elif capacity_percentage >= 85:
            report += """
  ⚠️  ELEVATED MONITORING
  - Increase security presence
  - Prepare crowd control measures
  - Monitor entry/exit flows
  - Ready emergency response team
  - Consider entry restrictions
"""
        else:
            report += """
  ✓ NORMAL OPERATIONS
  - Continue regular monitoring
  - Maintain situational awareness
  - Monitor for sudden changes
"""
        
        report += f"\n{'='*60}\n"
        
        return report


def main():
    """Main demo function"""
    demo = CrowdDemo()
    
    print("\n" + "="*60)
    print("Welcome to Crowd Control System Demo")
    print("="*60)
    print("\nThis demo simulates different crowd scenarios")
    print("to demonstrate the system's capabilities.")
    print("\nNo actual video processing - just visualization")
    
    input("\nPress Enter to continue...")
    
    demo.run_demo()
    
    print("\nThank you for trying the Crowd Control System!")
    print("For actual deployment, use crowd_control.py")


if __name__ == "__main__":
    main()
