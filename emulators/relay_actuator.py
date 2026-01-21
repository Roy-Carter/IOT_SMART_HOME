"""
Relay Actuator Emulator
Simulates a relay switch that can be controlled via MQTT commands
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
    """MQTT client wrapper for relay actuator communication"""
    
    def __init__(self):
        self.broker = BROKER_IP
        self.port = BROKER_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.client_id = f"relay_actuator_{random.randint(10000, 99999)}"
        self.client = None
        self.connected = False
        self.message_callback = None
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for connection"""
        if rc == 0:
            self.connected = True
            print(f"[Relay] Connected to broker: {self.broker}")
        else:
            print(f"[Relay] Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        print(f"[Relay] Disconnected from broker")
    
    def on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            print(f"[Relay] Received command: {payload}")
            if self.message_callback:
                self.message_callback(payload)
        except Exception as e:
            print(f"[Relay] Error parsing message: {e}")
    
    def connect_to_broker(self, subscribe_topic=None):
        """Connect to MQTT broker and optionally subscribe to control topic"""
        try:
            self.client = mqtt.Client(self.client_id, clean_session=True)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            
            if subscribe_topic:
                self.client.subscribe(subscribe_topic)
            
            return True
        except Exception as e:
            print(f"[Relay] Connection error: {e}")
            return False
    
    def publish_data(self, topic, payload):
        """Publish data to MQTT topic"""
        if self.connected and self.client:
            try:
                self.client.publish(topic, payload, qos=1)
                return True
            except Exception as e:
                print(f"[Relay] Publish error: {e}")
                return False
        return False
    
    def set_message_callback(self, callback):
        """Set callback function for received messages"""
        self.message_callback = callback
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class RelayActuator(QMainWindow):
    """Relay Actuator Emulator GUI"""
    
    def __init__(self):
        super().__init__()
        self.mqtt_client = MqttClient()
        self.mqtt_client.set_message_callback(self.handle_control_command)
        self.is_active = False
        self.relay_state = False  # False = OFF, True = ON
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('Relay Switch Actuator Emulator')
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
        self.topic_input.setText(TOPICS['relay_actuator'])
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        
        connection_layout.addRow("Broker IP:", self.broker_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("Topic:", self.topic_input)
        connection_layout.addRow("", self.connect_btn)
        connection_group.setLayout(connection_layout)
        
        # Relay control section
        control_group = QGroupBox("Relay Control")
        control_layout = QVBoxLayout()
        
        self.on_btn = QPushButton("TURN ON")
        self.on_btn.setMinimumHeight(60)
        self.on_btn.clicked.connect(lambda: self.set_relay_state(True))
        self.on_btn.setStyleSheet("background-color: #95a5a6; color: white; font-size: 14px; font-weight: bold;")
        
        self.off_btn = QPushButton("TURN OFF")
        self.off_btn.setMinimumHeight(60)
        self.off_btn.clicked.connect(lambda: self.set_relay_state(False))
        self.off_btn.setStyleSheet("background-color: #95a5a6; color: white; font-size: 14px; font-weight: bold;")
        
        self.state_label = QLabel("Relay State: OFF")
        self.state_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c;")
        self.state_label.setAlignment(Qt.AlignCenter)
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-size: 12px;")
        
        control_layout.addWidget(self.state_label)
        control_layout.addWidget(self.on_btn)
        control_layout.addWidget(self.off_btn)
        control_layout.addWidget(self.status_label)
        control_group.setLayout(control_layout)
        
        # Assemble layout
        layout.addWidget(connection_group)
        layout.addWidget(control_group)
        layout.addStretch()
        main_widget.setLayout(layout)
    
    def toggle_connection(self):
        """Toggle MQTT connection"""
        if not self.is_active:
            # Connect
            self.mqtt_client.broker = self.broker_input.text()
            self.mqtt_client.port = int(self.port_input.text())
            control_topic = f"{self.topic_input.text()}/control"
            if self.mqtt_client.connect_to_broker(subscribe_topic=control_topic):
                self.is_active = True
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("background-color: #2ecc71; color: white;")
                self.status_label.setText("Status: Connected")
                self.status_label.setStyleSheet("font-size: 12px; color: #2ecc71;")
        else:
            # Disconnect
            self.is_active = False
            self.mqtt_client.disconnect()
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-size: 12px;")
    
    def set_relay_state(self, state):
        """Set relay state and publish status"""
        if self.is_active and self.mqtt_client.connected:
            self.relay_state = state
            state_text = "ON" if state else "OFF"
            
            # Update UI
            if state:
                self.state_label.setText("Relay State: ON")
                self.state_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2ecc71;")
                self.on_btn.setStyleSheet("background-color: #2ecc71; color: white; font-size: 14px; font-weight: bold;")
                self.off_btn.setStyleSheet("background-color: #95a5a6; color: white; font-size: 14px; font-weight: bold;")
            else:
                self.state_label.setText("Relay State: OFF")
                self.state_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c;")
                self.on_btn.setStyleSheet("background-color: #95a5a6; color: white; font-size: 14px; font-weight: bold;")
                self.off_btn.setStyleSheet("background-color: #e74c3c; color: white; font-size: 14px; font-weight: bold;")
            
            # Create payload
            payload = {
                "device_type": "Relay_Actuator",
                "device_id": self.mqtt_client.client_id,
                "timestamp": datetime.now().isoformat(),
                "action": "turn_on" if state else "turn_off",
                "state": state_text,
                "value": 1 if state else 0
            }
            
            # Publish to MQTT
            topic = self.topic_input.text()
            self.mqtt_client.publish_data(topic, json.dumps(payload))
            print(f"[Relay] State changed to: {state_text}")
    
    def handle_control_command(self, payload):
        """Handle incoming control commands"""
        try:
            command = payload.get('command', '').lower()
            if command == 'on' or command == 'turn_on':
                self.set_relay_state(True)
            elif command == 'off' or command == 'turn_off':
                self.set_relay_state(False)
        except Exception as e:
            print(f"[Relay] Error handling command: {e}")
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        if self.is_active:
            self.mqtt_client.disconnect()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RelayActuator()
    window.show()
    sys.exit(app.exec_())
