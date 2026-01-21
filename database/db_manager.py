"""
Database Manager Module
Handles all database operations for the IoT Smart Office system
"""
import sqlite3
import os
import threading
from datetime import datetime
from config.db_config import DB_PATH, SENSOR_DATA_TABLE, ACTUATOR_DATA_TABLE, ALERT_LOG_TABLE, SYSTEM_LOG_TABLE


class DatabaseManager:
    """Manages database connections and operations (thread-safe)"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database with required tables"""
        try:
            # Create thread-safe connection
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute(SENSOR_DATA_TABLE)
            conn.execute(ACTUATOR_DATA_TABLE)
            conn.execute(ALERT_LOG_TABLE)
            conn.execute(SYSTEM_LOG_TABLE)
            conn.commit()
            conn.close()
            print(f"Database initialized successfully: {self.db_path}")
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    
    def get_connection(self):
        """Get thread-safe database connection"""
        # Create a new connection for each thread
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return conn
    
    def close_connection(self):
        """Close database connection"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            self.conn = None
    
    def insert_sensor_data(self, device_type, device_id, topic, temperature=None, 
                          humidity=None, value=None, status=None, message=None):
        """Insert sensor data into database (thread-safe)"""
        try:
            with self._lock:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sensor_data 
                    (timestamp, device_type, device_id, topic, temperature, humidity, value, status, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, device_type, device_id, topic, temperature, humidity, value, status, message))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            print(f"Error inserting sensor data: {e}")
            return False
    
    def insert_actuator_data(self, device_type, device_id, topic, action=None, 
                            state=None, value=None):
        """Insert actuator data into database (thread-safe)"""
        try:
            with self._lock:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO actuator_data 
                    (timestamp, device_type, device_id, topic, action, state, value)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, device_type, device_id, topic, action, state, value))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            print(f"Error inserting actuator data: {e}")
            return False
    
    def insert_alert(self, alert_type, severity, device_type=None, device_id=None, 
                    topic=None, message=None, value=None, threshold=None):
        """Insert alert into database (thread-safe)"""
        try:
            with self._lock:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alert_log 
                    (timestamp, alert_type, severity, device_type, device_id, topic, message, value, threshold)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, alert_type, severity, device_type, device_id, topic, message, value, threshold))
                conn.commit()
                last_id = cursor.lastrowid
                conn.close()
            return last_id
        except Exception as e:
            print(f"Error inserting alert: {e}")
            return None
    
    def insert_system_log(self, log_level, component, message):
        """Insert system log entry (thread-safe)"""
        try:
            with self._lock:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_log (timestamp, log_level, component, message)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, log_level, component, message))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            print(f"Error inserting system log: {e}")
            return False
    
    def get_recent_sensor_data(self, limit=100, device_type=None):
        """Get recent sensor data (thread-safe)"""
        try:
            with self._lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                if device_type:
                    cursor.execute("""
                        SELECT * FROM sensor_data 
                        WHERE device_type = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (device_type, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM sensor_data 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                result = cursor.fetchall()
                conn.close()
            return result
        except Exception as e:
            print(f"Error fetching sensor data: {e}")
            return []
    
    def get_recent_alerts(self, limit=50, severity=None, acknowledged=None):
        """Get recent alerts (thread-safe)"""
        try:
            with self._lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                query = "SELECT * FROM alert_log WHERE 1=1"
                params = []
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity)
                if acknowledged is not None:
                    query += " AND acknowledged = ?"
                    params.append(acknowledged)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                result = cursor.fetchall()
                conn.close()
            return result
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id):
        """Mark alert as acknowledged (thread-safe)"""
        try:
            with self._lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alert_log 
                    SET acknowledged = 1 
                    WHERE id = ?
                """, (alert_id,))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            print(f"Error acknowledging alert: {e}")
            return False

    def get_table_names(self):
        """Get all table names from the database."""
        try:
            with self._lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
            # Filter out sqlite sequence table
            return [table for table in tables if table != 'sqlite_sequence']
        except Exception as e:
            print(f"Error fetching table names: {e}")
            return []

    def get_table_content(self, table_name):
        """Get column headers and all rows for a given table."""
        # Basic security check to prevent SQL injection
        if not table_name or not table_name.isidentifier():
            print(f"Invalid table name provided: {table_name}")
            return [], []
        
        try:
            with self._lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Get headers in a safe way
                cursor.execute(f"PRAGMA table_info('{table_name}');")
                headers = [row[1] for row in cursor.fetchall()]
                
                # Get data using parameterized query for safety, even if just table name
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 500;")
                rows = cursor.fetchall()
                
                conn.close()
            return headers, rows
        except Exception as e:
            print(f"Error fetching content for table '{table_name}': {e}")
            return [], []
