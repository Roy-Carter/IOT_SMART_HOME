"""
MQTT Configuration Module
Contains broker connection settings and topic definitions
"""
import socket

# Broker configuration
BROKER_SELECTION = 1  # 0 - HIT broker, 1 - open HiveMQ broker

BROKERS = [
    str(socket.gethostbyname('vmm1.saaintertrade.com')), 
    str(socket.gethostbyname('broker.hivemq.com'))
]
PORTS = ['80', '1883']
USERNAMES = ['MATZI', '']
PASSWORDS = ['MATZI', '']

# Selected broker configuration
BROKER_IP = BROKERS[BROKER_SELECTION]
BROKER_PORT = int(PORTS[BROKER_SELECTION])
MQTT_USERNAME = USERNAMES[BROKER_SELECTION]
MQTT_PASSWORD = PASSWORDS[BROKER_SELECTION]

# Topic configuration
TOPIC_NAMESPACE = 'smart_office'
TOPICS = {
    'dht_sensor': f'{TOPIC_NAMESPACE}/sensors/dht',
    'button_actuator': f'{TOPIC_NAMESPACE}/actuators/button',
    'relay_actuator': f'{TOPIC_NAMESPACE}/actuators/relay',
    'warnings': f'{TOPIC_NAMESPACE}/alerts/warnings',
    'alarms': f'{TOPIC_NAMESPACE}/alerts/alarms',
    'data_manager': f'{TOPIC_NAMESPACE}/manager/status',
    'all_sensors': f'{TOPIC_NAMESPACE}/sensors/+',
    'all_actuators': f'{TOPIC_NAMESPACE}/actuators/+',
    'all_topics': f'{TOPIC_NAMESPACE}/#'
}

# Connection timeout
CONNECTION_TIMEOUT = 0  # 0 stands for endless
