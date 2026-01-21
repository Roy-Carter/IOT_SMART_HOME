"""
Database Configuration Module
Contains database connection settings and table schemas
"""
import os

# Database configuration
DB_DIR = 'database'
DB_NAME = 'iot_smart_office.db'
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# Ensure database directory exists
os.makedirs(DB_DIR, exist_ok=True)

# Table schemas
SENSOR_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    value REAL,
    status TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

ACTUATOR_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS actuator_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    action TEXT,
    state TEXT,
    value TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

ALERT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    device_type TEXT,
    device_id TEXT,
    topic TEXT,
    message TEXT,
    value REAL,
    threshold REAL,
    acknowledged INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

SYSTEM_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS system_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    log_level TEXT NOT NULL,
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""
