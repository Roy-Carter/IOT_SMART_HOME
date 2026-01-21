"""
Data Manager Application
Collects data from MQTT broker, stores in database, and processes warnings/alarms
"""
import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import paho.mqtt.client as mqtt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.mqtt_config import BROKER_IP, BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, TOPICS
from database.db_manager import DatabaseManager


class MqttDataCollector:
    """MQTT client for data collection"""
    
    def __init__(self, db_manager, alert_callback=None):
        self.broker = BROKER_IP
        self.port = BROKER_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.client_id = f"data_collector_{os.getpid()}"
        self.client = None
        self.connected = False
        self.db_manager = db_manager
        self.alert_callback = alert_callback
        self.message_count = 0
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for connection"""
        if rc == 0:
            self.connected = True
            print(f"[Data Manager] Connected to broker: {self.broker}")
            # Subscribe to all relevant topics
            self.client.subscribe(TOPICS['all_topics'])
            print(f"[Data Manager] Subscribed to: {TOPICS['all_topics']}")
        else:
            print(f"[Data Manager] Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        print(f"[Data Manager] Disconnected from broker")
    
    def on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            self.message_count += 1
            self.process_message(topic, payload)
        except json.JSONDecodeError:
            # Handle non-JSON messages
            try:
                payload = msg.payload.decode('utf-8')
                self.message_count += 1
                self.process_text_message(topic, payload)
            except Exception as e:
                print(f"[Data Manager] Error processing message: {e}")
        except Exception as e:
            print(f"[Data Manager] Error in on_message: {e}")
    
    def process_message(self, topic, payload):
        """Process received MQTT message"""
        device_type = payload.get('device_type', 'Unknown')
        device_id = payload.get('device_id', 'unknown')
        
        # Store sensor data
        if 'DHT_Sensor' in device_type or 'temperature' in payload or 'humidity' in payload:
            temp = payload.get('temperature')
            humidity = payload.get('humidity')
            self.db_manager.insert_sensor_data(
                device_type=device_type,
                device_id=device_id,
                topic=topic,
                temperature=temp,
                humidity=humidity,
                message=json.dumps(payload)
            )
            # Check for warnings/alarms
            self.check_temperature_humidity_thresholds(temp, humidity, device_id, topic)
        
        # Store actuator data
        elif 'Actuator' in device_type or 'button' in device_type.lower() or 'relay' in device_type.lower():
            action = payload.get('action', '')
            state = payload.get('state', '')
            value = payload.get('value', '')
            self.db_manager.insert_actuator_data(
                device_type=device_type,
                device_id=device_id,
                topic=topic,
                action=action,
                state=state,
                value=str(value)
            )
        
        # Log system message
        self.db_manager.insert_system_log(
            log_level='INFO',
            component='DataCollector',
            message=f"Received message from {device_type} on topic {topic}"
        )
    
    def process_text_message(self, topic, payload):
        """Process text-based messages"""
        self.db_manager.insert_system_log(
            log_level='INFO',
            component='DataCollector',
            message=f"Received text message on topic {topic}: {payload}"
        )
    
    def check_temperature_humidity_thresholds(self, temperature, humidity, device_id, topic):
        """Check temperature and humidity thresholds and generate alerts"""
        # Temperature thresholds
        temp_high_warning = 26.0
        temp_high_alarm = 28.0
        temp_low_warning = 20.0
        temp_low_alarm = 18.0
        
        # Humidity thresholds
        humidity_high_warning = 70.0
        humidity_high_alarm = 75.0
        humidity_low_warning = 40.0
        humidity_low_alarm = 30.0
        
        # Check temperature
        if temperature is not None:
            if temperature >= temp_high_alarm:
                self.create_alert('ALARM', 'High Temperature', device_id, topic, 
                                f"Critical: Temperature is {temperature}°C (Threshold: {temp_high_alarm}°C)",
                                temperature, temp_high_alarm)
            elif temperature >= temp_high_warning:
                self.create_alert('WARNING', 'High Temperature', device_id, topic,
                                f"Warning: Temperature is {temperature}°C (Threshold: {temp_high_warning}°C)",
                                temperature, temp_high_warning)
            elif temperature <= temp_low_alarm:
                self.create_alert('ALARM', 'Low Temperature', device_id, topic,
                                f"Critical: Temperature is {temperature}°C (Threshold: {temp_low_alarm}°C)",
                                temperature, temp_low_alarm)
            elif temperature <= temp_low_warning:
                self.create_alert('WARNING', 'Low Temperature', device_id, topic,
                                f"Warning: Temperature is {temperature}°C (Threshold: {temp_low_warning}°C)",
                                temperature, temp_low_warning)
        
        # Check humidity
        if humidity is not None:
            if humidity >= humidity_high_alarm:
                self.create_alert('ALARM', 'High Humidity', device_id, topic,
                                f"Critical: Humidity is {humidity}% (Threshold: {humidity_high_alarm}%)",
                                humidity, humidity_high_alarm)
            elif humidity >= humidity_high_warning:
                self.create_alert('WARNING', 'High Humidity', device_id, topic,
                                f"Warning: Humidity is {humidity}% (Threshold: {humidity_high_warning}%)",
                                humidity, humidity_high_warning)
            elif humidity <= humidity_low_alarm:
                self.create_alert('ALARM', 'Low Humidity', device_id, topic,
                                f"Critical: Humidity is {humidity}% (Threshold: {humidity_low_alarm}%)",
                                humidity, humidity_low_alarm)
            elif humidity <= humidity_low_warning:
                self.create_alert('WARNING', 'Low Humidity', device_id, topic,
                                f"Warning: Humidity is {humidity}% (Threshold: {humidity_low_warning}%)",
                                humidity, humidity_low_warning)
    
    def create_alert(self, severity, alert_type, device_id, topic, message, value, threshold):
        """Create and store alert"""
        alert_id = self.db_manager.insert_alert(
            alert_type=alert_type,
            severity=severity,
            device_type='DHT_Sensor',
            device_id=device_id,
            topic=topic,
            message=message,
            value=value,
            threshold=threshold
        )
        
        # Publish alert to MQTT
        if self.connected:
            alert_topic = TOPICS['alarms'] if severity == 'ALARM' else TOPICS['warnings']
            alert_payload = {
                'alert_id': alert_id,
                'severity': severity,
                'alert_type': alert_type,
                'device_id': device_id,
                'message': message,
                'value': value,
                'threshold': threshold,
                'timestamp': datetime.now().isoformat()
            }
            self.client.publish(alert_topic, json.dumps(alert_payload), qos=1)
        
        # Callback for GUI updates
        if self.alert_callback:
            self.alert_callback(severity, alert_type, message)
    
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
            print(f"[Data Manager] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class DataManagerGUI(QMainWindow):
    """Data Manager GUI Application"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.data_collector = MqttDataCollector(self.db_manager, self.on_alert_received)
        self.is_running = False
        self.init_ui()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.setInterval(2000)  # Update every 2 seconds
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('IoT Smart Office - Data Manager')
        self.setGeometry(100, 100, 700, 600)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # Connection section
        connection_group = QGroupBox("MQTT Connection")
        connection_layout = QFormLayout()
        
        self.broker_input = QLineEdit()
        self.broker_input.setText(BROKER_IP)
        self.broker_input.setInputMask('999.999.999.999')
        
        self.port_input = QLineEdit()
        self.port_input.setText(str(BROKER_PORT))
        self.port_input.setValidator(QIntValidator(1, 65535))
        
        self.start_btn = QPushButton("Start Data Collection")
        self.start_btn.clicked.connect(self.toggle_collection)
        self.start_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px;")
        
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        connection_layout.addRow("Broker IP:", self.broker_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("", self.start_btn)
        connection_layout.addRow("", self.status_label)
        connection_group.setLayout(connection_layout)
        
        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout()
        
        self.messages_label = QLabel("Messages Received: 0")
        self.messages_label.setStyleSheet("font-size: 12px;")
        
        self.sensor_data_label = QLabel("Sensor Records: 0")
        self.sensor_data_label.setStyleSheet("font-size: 12px;")
        
        self.actuator_data_label = QLabel("Actuator Records: 0")
        self.actuator_data_label.setStyleSheet("font-size: 12px;")
        
        self.alerts_label = QLabel("Total Alerts: 0")
        self.alerts_label.setStyleSheet("font-size: 12px;")
        
        self.warnings_label = QLabel("Warnings: 0")
        self.warnings_label.setStyleSheet("font-size: 12px; color: #f39c12;")
        
        self.alarms_label = QLabel("Alarms: 0")
        self.alarms_label.setStyleSheet("font-size: 12px; color: #e74c3c; font-weight: bold;")
        
        stats_layout.addWidget(self.messages_label, 0, 0)
        stats_layout.addWidget(self.sensor_data_label, 0, 1)
        stats_layout.addWidget(self.actuator_data_label, 1, 0)
        stats_layout.addWidget(self.alerts_label, 1, 1)
        stats_layout.addWidget(self.warnings_label, 2, 0)
        stats_layout.addWidget(self.alarms_label, 2, 1)
        stats_group.setLayout(stats_layout)
        
        # Recent alerts section
        alerts_group = QGroupBox("Recent Alerts")
        alerts_layout = QVBoxLayout()
        
        self.alerts_list = QTextEdit()
        self.alerts_list.setReadOnly(True)
        self.alerts_list.setMaximumHeight(200)
        alerts_layout.addWidget(self.alerts_list)
        alerts_group.setLayout(alerts_layout)
        
        # Assemble layout
        layout.addWidget(connection_group)
        layout.addWidget(stats_group)
        layout.addWidget(alerts_group)
        layout.addStretch()
        main_widget.setLayout(layout)
    
    def toggle_collection(self):
        """Toggle data collection"""
        if not self.is_running:
            # Start collection
            self.data_collector.broker = self.broker_input.text()
            self.data_collector.port = int(self.port_input.text())
            if self.data_collector.connect_to_broker():
                self.is_running = True
                self.start_btn.setText("Stop Data Collection")
                self.start_btn.setStyleSheet("background-color: #2ecc71; color: white; font-size: 14px;")
                self.status_label.setText("Status: Running")
                self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2ecc71;")
                self.update_timer.start()
                self.db_manager.insert_system_log('INFO', 'DataManager', 'Data collection started')
        else:
            # Stop collection
            self.is_running = False
            self.data_collector.disconnect()
            self.start_btn.setText("Start Data Collection")
            self.start_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-size: 14px;")
            self.status_label.setText("Status: Stopped")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            self.update_timer.stop()
            self.db_manager.insert_system_log('INFO', 'DataManager', 'Data collection stopped')
    
    def on_alert_received(self, severity, alert_type, message):
        """Handle alert callback"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color = "#e74c3c" if severity == 'ALARM' else "#f39c12"
        self.alerts_list.append(f'<span style="color: {color}; font-weight: bold;">[{timestamp}] {severity}: {message}</span>')
        # Keep only last 20 alerts visible
        text = self.alerts_list.toPlainText()
        if text.count('\n') > 20:
            lines = text.split('\n')
            self.alerts_list.setPlainText('\n'.join(lines[-20:]))
    
    def update_statistics(self):
        """Update statistics display"""
        if self.is_running:
            self.messages_label.setText(f"Messages Received: {self.data_collector.message_count}")
            
            # Get counts from database
            sensor_data = self.db_manager.get_recent_sensor_data(limit=1000)
            actuator_data = self.db_manager.get_recent_alerts(limit=1000)
            alerts = self.db_manager.get_recent_alerts(limit=1000)
            warnings = [a for a in alerts if len(a) > 3 and a[2] == 'WARNING']
            alarms = [a for a in alerts if len(a) > 3 and a[2] == 'ALARM']
            
            self.sensor_data_label.setText(f"Sensor Records: {len(sensor_data)}")
            self.actuator_data_label.setText(f"Actuator Records: {len(actuator_data)}")
            self.alerts_label.setText(f"Total Alerts: {len(alerts)}")
            self.warnings_label.setText(f"Warnings: {len(warnings)}")
            self.alarms_label.setText(f"Alarms: {len(alarms)}")
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        if self.is_running:
            self.data_collector.disconnect()
            self.db_manager.insert_system_log('INFO', 'DataManager', 'Application closed')
        self.db_manager.close_connection()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DataManagerGUI()
    window.show()
    sys.exit(app.exec_())
