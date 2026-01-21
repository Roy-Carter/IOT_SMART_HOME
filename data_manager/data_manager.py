"""
Data Manager Application
Collects data from MQTT broker, stores it in database, and processes warnings/alarms
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


class DataManagerMQTT:
    """MQTT client for data manager"""
    
    def __init__(self, message_handler):
        self.broker = BROKER_IP
        self.port = BROKER_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.client_id = f"data_manager_{random.randint(10000, 99999)}"
        self.client = None
        self.connected = False
        self.message_handler = message_handler
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for connection"""
        if rc == 0:
            self.connected = True
            print(f"[DataManager] Connected to broker: {self.broker}")
            # Subscribe to all sensor and actuator topics
            client.subscribe(TOPICS['all_topics'])
        else:
            print(f"[DataManager] Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        print(f"[DataManager] Disconnected from broker")
    
    def on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            payload = json.loads(payload_str)
            self.message_handler(topic, payload)
        except json.JSONDecodeError:
            print(f"[DataManager] Invalid JSON received: {payload_str}")
        except Exception as e:
            print(f"[DataManager] Error processing message: {e}")
    
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
            print(f"[DataManager] Connection error: {e}")
            return False
    
    def publish_warning(self, message):
        """Publish warning message"""
        if self.connected and self.client:
            try:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "severity": "warning",
                    "message": message
                }
                self.client.publish(TOPICS['warnings'], json.dumps(payload), qos=1)
                return True
            except Exception as e:
                print(f"[DataManager] Warning publish error: {e}")
                return False
        return False
    
    def publish_alarm(self, message):
        """Publish alarm message"""
        if self.connected and self.client:
            try:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "severity": "alarm",
                    "message": message
                }
                self.client.publish(TOPICS['alarms'], json.dumps(payload), qos=1)
                return True
            except Exception as e:
                print(f"[DataManager] Alarm publish error: {e}")
                return False
        return False
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class DataManagerApp(QMainWindow):
    """Data Manager Application GUI"""
    
    # Signal for thread-safe log updates
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.mqtt_client = None
        self.is_active = False
        self.data_count = 0
        self.warning_count = 0
        self.alarm_count = 0
        # Connect signal to slot
        self.log_signal.connect(self.log_message_thread_safe)
        
        # Thresholds for warnings and alarms
        self.temp_warning_low = 18.0
        self.temp_warning_high = 28.0
        self.temp_alarm_low = 15.0
        self.temp_alarm_high = 32.0
        self.humidity_warning_low = 35.0
        self.humidity_warning_high = 70.0
        self.humidity_alarm_low = 25.0
        self.humidity_alarm_high = 85.0
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('IoT Smart Office - Data Manager')
        self.setGeometry(100, 100, 900, 700)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # Connection section
        connection_group = QGroupBox("MQTT Connection")
        connection_layout = QFormLayout()
        
        self.broker_input = QLineEdit()
        self.broker_input.setText(BROKER_IP)
        
        self.port_input = QLineEdit()
        self.port_input.setText(str(BROKER_PORT))
        self.port_input.setValidator(QIntValidator(1, 65535))
        
        self.connect_btn = QPushButton("Start Data Collection")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px; padding: 5px;")
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-size: 12px;")
        
        connection_layout.addRow("Broker IP:", self.broker_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("", self.connect_btn)
        connection_layout.addRow("", self.status_label)
        connection_group.setLayout(connection_layout)
        
        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout()
        
        self.data_count_label = QLabel("Data Records: 0")
        self.data_count_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.warning_count_label = QLabel("Warnings: 0")
        self.warning_count_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f39c12;")
        
        self.alarm_count_label = QLabel("Alarms: 0")
        self.alarm_count_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")
        
        stats_layout.addWidget(self.data_count_label, 0, 0)
        stats_layout.addWidget(self.warning_count_label, 0, 1)
        stats_layout.addWidget(self.alarm_count_label, 0, 2)
        stats_group.setLayout(stats_layout)
        
        # Thresholds section
        thresholds_group = QGroupBox("Alert Thresholds")
        thresholds_layout = QFormLayout()
        
        self.temp_low_alarm = QLineEdit(str(self.temp_alarm_low))
        self.temp_low_warning = QLineEdit(str(self.temp_warning_low))
        self.temp_high_warning = QLineEdit(str(self.temp_warning_high))
        self.temp_high_alarm = QLineEdit(str(self.temp_alarm_high))
        
        self.hum_low_alarm = QLineEdit(str(self.humidity_alarm_low))
        self.hum_low_warning = QLineEdit(str(self.humidity_warning_low))
        self.hum_high_warning = QLineEdit(str(self.humidity_warning_high))
        self.hum_high_alarm = QLineEdit(str(self.humidity_alarm_high))
        
        thresholds_layout.addRow("Temp Alarm Low:", self.temp_low_alarm)
        thresholds_layout.addRow("Temp Warning Low:", self.temp_low_warning)
        thresholds_layout.addRow("Temp Warning High:", self.temp_high_warning)
        thresholds_layout.addRow("Temp Alarm High:", self.temp_high_alarm)
        thresholds_layout.addRow("Humidity Alarm Low:", self.hum_low_alarm)
        thresholds_layout.addRow("Humidity Warning Low:", self.hum_low_warning)
        thresholds_layout.addRow("Humidity Warning High:", self.hum_high_warning)
        thresholds_layout.addRow("Humidity Alarm High:", self.hum_high_alarm)
        
        update_thresholds_btn = QPushButton("Update Thresholds")
        update_thresholds_btn.clicked.connect(self.update_thresholds)
        thresholds_layout.addRow("", update_thresholds_btn)
        thresholds_group.setLayout(thresholds_layout)
        
        # Activity log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(clear_log_btn)
        log_group.setLayout(log_layout)
        
        # Assemble layout
        layout.addWidget(connection_group)
        layout.addWidget(stats_group)
        layout.addWidget(thresholds_group)
        layout.addWidget(log_group)
        layout.addStretch()
        main_widget.setLayout(layout)
    
    def toggle_connection(self):
        """Toggle MQTT connection"""
        if not self.is_active:
            # Connect
            self.mqtt_client = DataManagerMQTT(self.handle_message)
            self.mqtt_client.broker = self.broker_input.text()
            self.mqtt_client.port = int(self.port_input.text())
            
            if self.mqtt_client.connect_to_broker():
                self.is_active = True
                self.connect_btn.setText("Stop Data Collection")
                self.connect_btn.setStyleSheet("background-color: #2ecc71; color: white; font-size: 14px; padding: 5px;")
                self.status_label.setText("Status: Connected and Collecting Data")
                self.status_label.setStyleSheet("font-size: 12px; color: #2ecc71;")
                self.log_message("Data Manager started - Listening for MQTT messages")
        else:
            # Disconnect
            self.is_active = False
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            self.connect_btn.setText("Start Data Collection")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px; padding: 5px;")
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-size: 12px;")
            self.log_message("Data Manager stopped")
    
    def handle_message(self, topic, payload):
        """Handle incoming MQTT messages"""
        try:
            device_type = payload.get('device_type', 'Unknown')
            device_id = payload.get('device_id', 'Unknown')
            timestamp = payload.get('timestamp', datetime.now().isoformat())
            
            # Store sensor data
            if 'DHT_Sensor' in device_type or 'temperature' in payload or 'humidity' in payload:
                temp = payload.get('temperature')
                humidity = payload.get('humidity')
                
                # Store in database
                self.db_manager.insert_sensor_data(
                    device_type=device_type,
                    device_id=device_id,
                    topic=topic,
                    temperature=temp,
                    humidity=humidity
                )
                self.data_count += 1
                self.update_statistics()
                
                # Process alerts for temperature
                if temp is not None:
                    if temp <= self.temp_alarm_low or temp >= self.temp_alarm_high:
                        alert_msg = f"ALARM: Temperature {temp}°C is out of safe range!"
                        self.db_manager.insert_alert(
                            alert_type="Temperature",
                            severity="alarm",
                            device_type=device_type,
                            device_id=device_id,
                            topic=topic,
                            message=alert_msg,
                            value=temp,
                            threshold=self.temp_alarm_low if temp <= self.temp_alarm_low else self.temp_alarm_high
                        )
                        self.mqtt_client.publish_alarm(alert_msg)
                        self.alarm_count += 1
                        self.log_message(f"ALARM: {alert_msg}")
                    elif temp <= self.temp_warning_low or temp >= self.temp_warning_high:
                        alert_msg = f"WARNING: Temperature {temp}°C is approaching limits"
                        self.db_manager.insert_alert(
                            alert_type="Temperature",
                            severity="warning",
                            device_type=device_type,
                            device_id=device_id,
                            topic=topic,
                            message=alert_msg,
                            value=temp,
                            threshold=self.temp_warning_low if temp <= self.temp_warning_low else self.temp_warning_high
                        )
                        self.mqtt_client.publish_warning(alert_msg)
                        self.warning_count += 1
                        self.log_message(f"WARNING: {alert_msg}")
                
                # Process alerts for humidity
                if humidity is not None:
                    if humidity <= self.humidity_alarm_low or humidity >= self.humidity_alarm_high:
                        alert_msg = f"ALARM: Humidity {humidity}% is out of safe range!"
                        self.db_manager.insert_alert(
                            alert_type="Humidity",
                            severity="alarm",
                            device_type=device_type,
                            device_id=device_id,
                            topic=topic,
                            message=alert_msg,
                            value=humidity,
                            threshold=self.humidity_alarm_low if humidity <= self.humidity_alarm_low else self.humidity_alarm_high
                        )
                        self.mqtt_client.publish_alarm(alert_msg)
                        self.alarm_count += 1
                        self.log_message(f"ALARM: {alert_msg}")
                    elif humidity <= self.humidity_warning_low or humidity >= self.humidity_warning_high:
                        alert_msg = f"WARNING: Humidity {humidity}% is approaching limits"
                        self.db_manager.insert_alert(
                            alert_type="Humidity",
                            severity="warning",
                            device_type=device_type,
                            device_id=device_id,
                            topic=topic,
                            message=alert_msg,
                            value=humidity,
                            threshold=self.humidity_warning_low if humidity <= self.humidity_warning_low else self.humidity_warning_high
                        )
                        self.mqtt_client.publish_warning(alert_msg)
                        self.warning_count += 1
                        self.log_message(f"WARNING: {alert_msg}")
                
                self.log_message(f"Data stored: {device_type} - Temp: {temp}°C, Humidity: {humidity}%")
            
            # Store actuator data
            elif 'Actuator' in device_type or 'action' in payload or 'state' in payload:
                action = payload.get('action', '')
                state = payload.get('state', '')
                value = payload.get('value', '')
                
                # Store in database
                self.db_manager.insert_actuator_data(
                    device_type=device_type,
                    device_id=device_id,
                    topic=topic,
                    action=action,
                    state=state,
                    value=str(value)
                )
                self.data_count += 1
                self.update_statistics()
                self.log_message(f"Actuator data stored: {device_type} - {action} ({state})")
            
        except Exception as e:
            self.log_message(f"Error processing message: {e}")
            print(f"[DataManager] Error handling message: {e}")
    
    def update_thresholds(self):
        """Update alert thresholds"""
        try:
            self.temp_alarm_low = float(self.temp_low_alarm.text())
            self.temp_warning_low = float(self.temp_low_warning.text())
            self.temp_warning_high = float(self.temp_high_warning.text())
            self.temp_alarm_high = float(self.temp_high_alarm.text())
            
            self.humidity_alarm_low = float(self.hum_low_alarm.text())
            self.humidity_warning_low = float(self.hum_low_warning.text())
            self.humidity_warning_high = float(self.hum_high_warning.text())
            self.humidity_alarm_high = float(self.hum_high_alarm.text())
            
            self.log_message("Alert thresholds updated")
        except ValueError:
            self.log_message("Error: Invalid threshold values")
    
    def update_statistics(self):
        """Update statistics display"""
        self.data_count_label.setText(f"Data Records: {self.data_count}")
        self.warning_count_label.setText(f"Warnings: {self.warning_count}")
        self.alarm_count_label.setText(f"Alarms: {self.alarm_count}")
    
    def log_message(self, message):
        """Add message to activity log (thread-safe via signal)"""
        self.log_signal.emit(message)
    
    def log_message_thread_safe(self, message):
        """Thread-safe method to add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        if self.is_active and self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.db_manager:
            self.db_manager.close_connection()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DataManagerApp()
    window.show()
    sys.exit(app.exec_())
