"""
Main GUI Application
Shows real-time data changes and Info/Warning/Alarm status window
"""
import sys
import json
import random
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import paho.mqtt.client as mqtt
from datetime import datetime
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.mqtt_config import BROKER_IP, BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, TOPICS
from database.db_manager import DatabaseManager


class MainGUIMQTT:
    """MQTT client for main GUI"""
    
    def __init__(self, message_handler):
        self.broker = BROKER_IP
        self.port = BROKER_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.client_id = f"main_gui_{random.randint(10000, 99999)}"
        self.client = None
        self.connected = False
        self.message_handler = message_handler
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for connection"""
        if rc == 0:
            self.connected = True
            print(f"[MainGUI] Connected to broker: {self.broker}")
            # Subscribe to all topics
            client.subscribe(TOPICS['all_topics'])
        else:
            print(f"[MainGUI] Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        print(f"[MainGUI] Disconnected from broker")
    
    def on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            payload = json.loads(payload_str)
            self.message_handler(topic, payload)
        except json.JSONDecodeError:
            print(f"[MainGUI] Invalid JSON received: {payload_str}")
        except Exception as e:
            print(f"[MainGUI] Error processing message: {e}")
    
    def connect_to_broker(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(self.client_id, clean_session=True)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MainGUI] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class MainGUIApp(QMainWindow):
    """Main GUI Application"""
    
    # Signals for thread-safe UI updates
    info_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.mqtt_client = None
        self.is_active = False
        # Connect signal to slot
        self.info_signal.connect(self.add_info_thread_safe)
        
        # Current data
        self.current_temp = None
        self.current_humidity = None
        self.occupancy_state = "Unknown"
        self.ac_state = "Unknown"
        
        # Alerts
        self.warnings = []
        self.alarms = []
        
        self.init_ui()
        
        # Timer for refreshing data from database
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_from_database)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds for better sync
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('IoT Smart Office - Main Dashboard')
        self.setGeometry(100, 100, 1200, 800)
        
        # Main widget with horizontal splitter
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        
        # Left panel - Data visualization
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Connection section
        connection_group = QGroupBox("Connection")
        connection_layout = QFormLayout()
        
        self.broker_input = QLineEdit()
        self.broker_input.setText(BROKER_IP)
        
        self.port_input = QLineEdit()
        self.port_input.setText(str(BROKER_PORT))
        self.port_input.setValidator(QIntValidator(1, 65535))
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px; padding: 5px;")
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-size: 12px;")
        
        connection_layout.addRow("Broker IP:", self.broker_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("", self.connect_btn)
        connection_layout.addRow("", self.status_label)
        connection_group.setLayout(connection_layout)
        
        # Sensor data section
        sensor_group = QGroupBox("Sensor Data")
        sensor_layout = QVBoxLayout()
        
        # Temperature display
        temp_frame = QFrame()
        temp_layout = QVBoxLayout()
        temp_label_title = QLabel("Temperature")
        temp_label_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.temp_label = QLabel("--°C")
        self.temp_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #e74c3c;")
        self.temp_label.setAlignment(Qt.AlignCenter)
        temp_layout.addWidget(temp_label_title)
        temp_layout.addWidget(self.temp_label)
        temp_frame.setLayout(temp_layout)
        temp_frame.setStyleSheet("border: 2px solid #e74c3c; border-radius: 10px; padding: 10px;")
        
        # Humidity display
        hum_frame = QFrame()
        hum_layout = QVBoxLayout()
        hum_label_title = QLabel("Humidity")
        hum_label_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.humidity_label = QLabel("--%")
        self.humidity_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #3498db;")
        self.humidity_label.setAlignment(Qt.AlignCenter)
        hum_layout.addWidget(hum_label_title)
        hum_layout.addWidget(self.humidity_label)
        hum_frame.setLayout(hum_layout)
        hum_frame.setStyleSheet("border: 2px solid #3498db; border-radius: 10px; padding: 10px;")
        
        sensor_layout.addWidget(temp_frame)
        sensor_layout.addWidget(hum_frame)
        sensor_group.setLayout(sensor_layout)
        
        # Actuator status section
        actuator_group = QGroupBox("Device Status")
        actuator_layout = QFormLayout()
        
        self.occupancy_status_label = QLabel("Unknown")
        self.occupancy_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.ac_status_label = QLabel("Unknown")
        self.ac_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        actuator_layout.addRow("Office Occupancy:", self.occupancy_status_label)
        actuator_layout.addRow("AC Status:", self.ac_status_label)
        actuator_group.setLayout(actuator_layout)
        
        # Left panel layout
        left_layout.addWidget(connection_group)
        left_layout.addWidget(sensor_group)
        left_layout.addWidget(actuator_group)
        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        
        # Right panel - Alerts and Info
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Alerts section
        alerts_group = QGroupBox("Alerts & Status")
        alerts_layout = QVBoxLayout()
        
        # Tabs for Info, Warnings, Alarms
        self.alert_tabs = QTabWidget()
        
        # Info tab
        self.info_tab = QWidget()
        info_layout = QVBoxLayout()
        self.info_text = QListWidget()
        info_layout.addWidget(self.info_text)
        self.info_tab.setLayout(info_layout)
        self.alert_tabs.addTab(self.info_tab, "Info")
        
        # Warnings tab
        self.warning_tab = QWidget()
        warning_layout = QVBoxLayout()
        self.warning_text = QListWidget()
        warning_layout.addWidget(self.warning_text)
        self.warning_tab.setLayout(warning_layout)
        self.alert_tabs.addTab(self.warning_tab, "Warnings")
        
        # Alarms tab
        self.alarm_tab = QWidget()
        alarm_layout = QVBoxLayout()
        self.alarm_text = QListWidget()
        alarm_layout.addWidget(self.alarm_text)
        self.alarm_tab.setLayout(alarm_layout)
        self.alert_tabs.addTab(self.alarm_tab, "Alarms")
        
        alerts_layout.addWidget(self.alert_tabs)
        alerts_group.setLayout(alerts_layout)
        
        # System info
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout()
        
        self.db_status_label = QLabel("Connected")
        self.db_status_label.setStyleSheet("font-size: 12px; color: #2ecc71;")
        
        self.last_update_label = QLabel("Never")
        self.last_update_label.setStyleSheet("font-size: 12px;")
        
        system_layout.addRow("Database:", self.db_status_label)
        system_layout.addRow("Last Update:", self.last_update_label)
        system_group.setLayout(system_layout)
        
        right_layout.addWidget(alerts_group)
        right_layout.addWidget(system_group)
        right_panel.setLayout(right_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
    
    def toggle_connection(self):
        """Toggle MQTT connection"""
        if not self.is_active:
            # Connect
            self.mqtt_client = MainGUIMQTT(self.handle_message)
            self.mqtt_client.broker = self.broker_input.text()
            self.mqtt_client.port = int(self.port_input.text())
            
            if self.mqtt_client.connect_to_broker():
                self.is_active = True
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("background-color: #2ecc71; color: white; font-size: 14px; padding: 5px;")
                self.status_label.setText("Status: Connected")
                self.status_label.setStyleSheet("font-size: 12px; color: #2ecc71;")
                self.add_info("Connected to MQTT broker")
        else:
            # Disconnect
            self.is_active = False
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px; padding: 5px;")
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-size: 12px;")
            self.add_info("Disconnected from MQTT broker")
    
    def handle_message(self, topic, payload):
        """Handle incoming MQTT messages"""
        try:
            device_type = payload.get('device_type', 'Unknown')
            
            # Handle sensor data
            if 'DHT_Sensor' in device_type or 'temperature' in payload or 'humidity' in payload:
                if 'temperature' in payload:
                    self.current_temp = payload.get('temperature')
                    self.temp_label.setText(f"{self.current_temp}°C")
                
                if 'humidity' in payload:
                    self.current_humidity = payload.get('humidity')
                    self.humidity_label.setText(f"{self.current_humidity}%")
                
                self.add_info(f"Updated: {device_type} - Temp: {self.current_temp}°C, Humidity: {self.current_humidity}%")
            
            # Handle occupancy sensor
            elif 'Occupancy_Sensor' in device_type:
                occupancy_value = payload.get('occupancy', '')
                state_value = payload.get('state', 'Unknown')
                # Use occupancy field if available, otherwise use state
                if occupancy_value:
                    self.occupancy_state = occupancy_value
                    state_color = "#2ecc71" if occupancy_value == "Occupied" else "#95a5a6"
                    display_text = occupancy_value
                else:
                    self.occupancy_state = "Occupied" if state_value == "ON" else "Vacant"
                    state_color = "#2ecc71" if state_value == "ON" else "#95a5a6"
                    display_text = self.occupancy_state
                self.occupancy_status_label.setText(display_text)
                self.occupancy_status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {state_color};")
                self.add_info(f"Office occupancy changed: {display_text}")
            
            # Handle AC controller
            elif 'AC_Controller' in device_type:
                self.ac_state = payload.get('state', 'Unknown')
                state_color = "#2ecc71" if self.ac_state == "ON" else "#e74c3c"
                display_text = f"AC {self.ac_state}"
                self.ac_status_label.setText(display_text)
                self.ac_status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {state_color};")
                self.add_info(f"AC status changed: {display_text}")
            
            # Handle warnings - trigger immediate refresh from database for accurate count
            elif 'warnings' in topic or payload.get('severity') == 'warning':
                # Trigger immediate DB refresh to get accurate count and display
                QTimer.singleShot(100, self.refresh_from_database)
            
            # Handle alarms - trigger immediate refresh from database for accurate count
            elif 'alarms' in topic or payload.get('severity') == 'alarm':
                # Trigger immediate DB refresh to get accurate count and display
                QTimer.singleShot(100, self.refresh_from_database)
            
            self.last_update_label.setText(datetime.now().strftime('%H:%M:%S'))
            
        except Exception as e:
            print(f"[MainGUI] Error handling message: {e}")
    
    def refresh_from_database(self):
        """Refresh data from database"""
        try:
            # Get recent sensor data
            recent_data = self.db_manager.get_recent_sensor_data(limit=1)
            if recent_data:
                # recent_data is a list of tuples
                # Format: (id, timestamp, device_type, device_id, topic, temperature, humidity, value, status, message, created_at)
                row = recent_data[0]
                if row[5] is not None:  # temperature
                    self.current_temp = row[5]
                    self.temp_label.setText(f"{self.current_temp}°C")
                if row[6] is not None:  # humidity
                    self.current_humidity = row[6]
                    self.humidity_label.setText(f"{self.current_humidity}%")
            
            # Get ALL unacknowledged alerts (no limit) to get accurate count
            all_warnings = self.db_manager.get_recent_alerts(limit=1000, severity='warning', acknowledged=0)
            all_alarms = self.db_manager.get_recent_alerts(limit=1000, severity='alarm', acknowledged=0)
            
            # Get recent alerts for display (last 50)
            recent_warnings = all_warnings[:50] if len(all_warnings) > 50 else all_warnings
            recent_alarms = all_alarms[:50] if len(all_alarms) > 50 else all_alarms
            
            # Update warnings - use total count from database
            total_warning_count = len(all_warnings)
            if total_warning_count != len(self.warnings) or True:  # Always refresh from DB
                self.warning_text.clear()
                for alert in recent_warnings:
                    # Format: (id, timestamp, alert_type, severity, device_type, device_id, topic, message, value, threshold, acknowledged, created_at)
                    msg = f"[{alert[1]}] {alert[7]}"
                    item = QListWidgetItem(msg)
                    item.setBackground(QColor("#fff3cd"))  # Yellow
                    self.warning_text.addItem(item)
                self.warnings = [f"[{a[1]}] {a[7]}" for a in all_warnings]  # Sync list with DB
                self.alert_tabs.setTabText(1, f"Warnings ({total_warning_count})")
                if recent_warnings:
                    self.warning_text.scrollToBottom()

            # Update alarms - use total count from database
            total_alarm_count = len(all_alarms)
            if total_alarm_count != len(self.alarms) or True:  # Always refresh from DB
                self.alarm_text.clear()
                for alert in recent_alarms:
                    msg = f"[{alert[1]}] {alert[7]}"
                    item = QListWidgetItem(msg)
                    item.setBackground(QColor("#f8d7da"))  # Red
                    self.alarm_text.addItem(item)
                self.alarms = [f"[{a[1]}] {a[7]}" for a in all_alarms]  # Sync list with DB
                self.alert_tabs.setTabText(2, f"Alarms ({total_alarm_count})")
                if recent_alarms:
                    self.alarm_text.scrollToBottom()

        except Exception as e:
            print(f"[MainGUI] Error refreshing from database: {e}")
    
    def add_info(self, message):
        """Add info message (thread-safe via signal)"""
        self.info_signal.emit(message)
    
    def add_info_thread_safe(self, message):
        """Thread-safe method to add info message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        item = QListWidgetItem(f"[{timestamp}] {message}")
        item.setBackground(QColor("#d4edda"))  # Green
        self.info_text.addItem(item)
        self.info_text.scrollToBottom()
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        if self.is_active and self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.db_manager:
            self.db_manager.close_connection()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainGUIApp()
    window.show()
    sys.exit(app.exec_())
