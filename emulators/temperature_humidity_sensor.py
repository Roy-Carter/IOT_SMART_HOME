"""
Temperature and Humidity Sensor Emulator
Simulates a DHT sensor that publishes temperature and humidity data via MQTT
"""
import sys
import random
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.mqtt_config import BROKER_IP, BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, TOPICS


class MqttClient:
    """MQTT client wrapper for sensor communication"""
    
    def __init__(self):
        self.broker = BROKER_IP
        self.port = BROKER_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.client_id = f"temp_humidity_sensor_{random.randint(10000, 99999)}"
        self.client = None
        self.connected = False
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for connection"""
        if rc == 0:
            self.connected = True
            print(f"[Sensor] Connected to broker: {self.broker}")
        else:
            print(f"[Sensor] Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        print(f"[Sensor] Disconnected from broker")
    
    def connect_to_broker(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(self.client_id, clean_session=True)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[Sensor] Connection error: {e}")
            return False
    
    def publish_data(self, topic, payload):
        """Publish data to MQTT topic"""
        if self.connected and self.client:
            try:
                self.client.publish(topic, payload, qos=1)
                return True
            except Exception as e:
                print(f"[Sensor] Publish error: {e}")
                return False
        return False
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class TemperatureHumiditySensor(QMainWindow):
    """Temperature and Humidity Sensor Emulator GUI"""
    
    def __init__(self):
        super().__init__()
        self.mqtt_client = MqttClient()
        self.is_active = False
        self.base_temp = 22.0
        self.base_humidity = 55.0
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_sensor_data)
        self.timer.setInterval(5000)  # Update every 5 seconds
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('Temperature & Humidity Sensor Emulator')
        self.setGeometry(100, 100, 400, 350)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # Connection section
        connection_group = QGroupBox("Connection")
        connection_layout = QFormLayout()
        
        self.broker_input = QLineEdit()
        self.broker_input.setText(BROKER_IP)
        self.broker_input.setInputMask('999.999.999.999')
        
        self.port_input = QLineEdit()
        self.port_input.setText(str(BROKER_PORT))
        self.port_input.setValidator(QIntValidator(1, 65535))
        
        self.topic_input = QLineEdit()
        self.topic_input.setText(TOPICS['dht_sensor'])
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        
        connection_layout.addRow("Broker IP:", self.broker_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("Topic:", self.topic_input)
        connection_layout.addRow("", self.connect_btn)
        connection_group.setLayout(connection_layout)
        
        # Sensor data section
        data_group = QGroupBox("Sensor Data")
        data_layout = QFormLayout()
        
        self.temp_label = QLabel("22.0°C")
        self.temp_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e74c3c;")
        
        self.humidity_label = QLabel("55.0%")
        self.humidity_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #3498db;")
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-size: 12px;")
        
        data_layout.addRow("Temperature:", self.temp_label)
        data_layout.addRow("Humidity:", self.humidity_label)
        data_layout.addRow("", self.status_label)
        data_group.setLayout(data_layout)
        
        # Assemble layout
        layout.addWidget(connection_group)
        layout.addWidget(data_group)
        layout.addStretch()
        main_widget.setLayout(layout)
    
    def toggle_connection(self):
        """Toggle MQTT connection"""
        if not self.is_active:
            # Connect
            self.mqtt_client.broker = self.broker_input.text()
            self.mqtt_client.port = int(self.port_input.text())
            if self.mqtt_client.connect_to_broker():
                self.is_active = True
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("background-color: #2ecc71; color: white;")
                self.status_label.setText("Status: Connected")
                self.status_label.setStyleSheet("font-size: 12px; color: #2ecc71;")
                self.timer.start()
        else:
            # Disconnect
            self.is_active = False
            self.timer.stop()
            self.mqtt_client.disconnect()
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-size: 12px;")
    
    def update_sensor_data(self):
        """Update and publish sensor data"""
        if self.is_active and self.mqtt_client.connected:
            # Simulate realistic sensor readings with slight variations
            temp = round(self.base_temp + random.uniform(-2.0, 3.0), 1)
            humidity = round(self.base_humidity + random.uniform(-5.0, 8.0), 1)
            
            # Ensure reasonable ranges
            temp = max(18.0, min(30.0, temp))
            humidity = max(30.0, min(80.0, humidity))
            
            # Update UI
            self.temp_label.setText(f"{temp}°C")
            self.humidity_label.setText(f"{humidity}%")
            
            # Create payload
            payload = {
                "device_type": "DHT_Sensor",
                "device_id": self.mqtt_client.client_id,
                "timestamp": datetime.now().isoformat(),
                "temperature": temp,
                "humidity": humidity,
                "unit_temp": "Celsius",
                "unit_humidity": "Percent"
            }
            
            # Publish to MQTT
            topic = self.topic_input.text()
            self.mqtt_client.publish_data(topic, json.dumps(payload))
            print(f"[Sensor] Published: Temp={temp}°C, Humidity={humidity}%")
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        if self.is_active:
            self.mqtt_client.disconnect()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TemperatureHumiditySensor()
    window.show()
    sys.exit(app.exec_())
