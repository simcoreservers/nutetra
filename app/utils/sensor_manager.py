import io
import time
import smbus2
import threading
import logging
import json
import os
from app import scheduler
from app.models.sensor_reading import SensorReading
from app.models.settings import Settings
from flask import current_app
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Create a logger for this module
logger = logging.getLogger(__name__)

# I2C addresses for Atlas Scientific sensors
SENSOR_ADDRESSES = {
    'ph': 0x63,      # Default I2C address for EZO pH Circuit
    'ec': 0x64,      # Default I2C address for EZO EC Circuit
    'temp': 0x66,    # Default I2C address for EZO RTD Circuit
}

# Command codes for Atlas Scientific EZO sensors
READ_COMMAND = 'R'
CALIBRATION_COMMAND = 'Cal'
TEMPERATURE_COMPENSATION_COMMAND = 'T'
SLEEP_COMMAND = 'Sleep'

# Global I2C bus
bus = None

# Last readings cache
last_readings = {
    'ph': None,
    'ec': None,
    'temp': None
}

# Latest sensor readings (in-memory cache)
latest_readings = {
    'ph': None,
    'ec': None,
    'temp': None
}

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_sensors():
    """Initialize the sensor communication and start the reading schedule"""
    global bus
    try:
        # Initialize I2C bus
        bus = smbus2.SMBus(1)  # 1 indicates /dev/i2c-1
        logger.info("I2C bus initialized successfully")
        
        # Test communication with sensors
        for sensor_type, address in SENSOR_ADDRESSES.items():
            try:
                # Try to read from the sensor
                read_sensor(sensor_type)
                logger.info(f"{sensor_type.upper()} sensor detected at address 0x{address:02X}")
            except Exception as e:
                logger.warning(f"Could not communicate with {sensor_type.upper()} sensor: {e}")
        
        # Schedule regular sensor readings
        schedule_readings()
        
        # Take initial readings
        read_all_sensors()
        
        logger.info("Sensor subsystem initialized")
    except Exception as e:
        logger.error(f"Failed to initialize sensor subsystem: {e}")
        if 'bus' in locals() and bus:
            bus.close()
            bus = None

def schedule_readings():
    """Set up scheduled sensor readings"""
    # Schedule pH readings
    ph_interval = Settings.get('ph_check_interval', 300)
    scheduler.add_job(
        read_and_log_sensor,
        'interval',
        seconds=ph_interval,
        id='ph_reading',
        replace_existing=True,
        args=['ph']
    )
    
    # Schedule EC readings
    ec_interval = Settings.get('ec_check_interval', 300)
    scheduler.add_job(
        read_and_log_sensor,
        'interval',
        seconds=ec_interval,
        id='ec_reading',
        replace_existing=True,
        args=['ec']
    )
    
    # Schedule temperature readings
    temp_interval = Settings.get('temp_check_interval', 300)
    scheduler.add_job(
        read_and_log_sensor,
        'interval',
        seconds=temp_interval,
        id='temp_reading',
        replace_existing=True,
        args=['temp']
    )
    
    logger.info("Sensor reading schedules initialized")

def read_sensor(sensor_type):
    """Read a value from the specified sensor"""
    global bus
    
    if bus is None:
        raise Exception("I2C bus not initialized")
    
    if sensor_type not in SENSOR_ADDRESSES:
        raise ValueError(f"Unknown sensor type: {sensor_type}")
    
    address = SENSOR_ADDRESSES[sensor_type]
    
    # If it's not a temperature sensor, compensate for temperature
    if sensor_type != 'temp':
        temp_value = get_last_reading('temp', 25.0)  # Default to 25°C if not available
        send_command(address, f"{TEMPERATURE_COMPENSATION_COMMAND},{temp_value:.2f}")
        time.sleep(0.3)  # Wait for command to process
    
    # Send read command
    send_command(address, READ_COMMAND)
    
    # Wait for reading (different sensors have different response times)
    if sensor_type == 'ph':
        time.sleep(0.9)
    elif sensor_type == 'ec':
        time.sleep(0.6)
    else:
        time.sleep(0.6)
    
    # Read response
    response = read_response(address)
    
    # Process response based on sensor type
    if response.startswith('?'):
        raise Exception(f"Error reading {sensor_type} sensor: {response}")
    
    try:
        value = float(response)
        # Update last reading cache
        last_readings[sensor_type] = value
        return value
    except ValueError:
        raise Exception(f"Invalid response from {sensor_type} sensor: {response}")

def send_command(address, command):
    """Send a command to the specified I2C address"""
    global bus
    
    if bus is None:
        raise Exception("I2C bus not initialized")
    
    # Convert command to bytes
    cmd_bytes = command.encode()
    
    try:
        # Write each byte of the command
        for i in range(len(cmd_bytes)):
            bus.write_byte(address, cmd_bytes[i])
    except Exception as e:
        logger.error(f"Error sending command to device at address 0x{address:02X}: {e}")
        raise

def read_response(address):
    """Read a response from the specified I2C address"""
    global bus
    
    if bus is None:
        raise Exception("I2C bus not initialized")
    
    try:
        # First byte indicates the response length
        response_len = bus.read_byte(address)
        
        # Read the specified number of bytes
        response_bytes = bytearray()
        for i in range(response_len):
            response_bytes.append(bus.read_byte(address))
        
        # Convert bytes to string
        return response_bytes.decode().strip()
    except Exception as e:
        logger.error(f"Error reading response from device at address 0x{address:02X}: {e}")
        raise

def read_and_log_sensor(sensor_type):
    """Read a sensor and log the result to the database"""
    try:
        # Read from the sensor
        value = read_sensor(sensor_type)
        if value is None:
            logger.warning(f"Failed to read {sensor_type} sensor: no reading obtained")
            return
        
        # Log the reading
        SensorReading.add_reading(sensor_type, value)
        
        # Check if reading is out of range and notify if needed
        check_reading_range(sensor_type, value)
        
        # Broadcast to connected clients via Socket.IO
        from app import socketio
        socketio.emit('sensor_update', {sensor_type: value})
        
        logger.debug(f"Logged {sensor_type} reading: {value}")
    except Exception as e:
        logger.error(f"Error reading {sensor_type} sensor: {e}")

def check_reading_range(sensor_type, value):
    """Check if a sensor reading is out of range and notify if needed"""
    # Check if notifications are enabled
    if not Settings.get('notifications_enabled', True):
        return
    
    message = None
    
    # Check ranges based on sensor type
    if sensor_type == 'ph':
        setpoint = Settings.get('ph_setpoint', 6.0)
        buffer = Settings.get('ph_buffer', 0.2)
        min_val = setpoint - buffer
        max_val = setpoint + buffer
        
        if value < min_val:
            message = f"pH is low: {value:.2f} (below {min_val:.2f})"
        elif value > max_val:
            message = f"pH is high: {value:.2f} (above {max_val:.2f})"
            
    elif sensor_type == 'ec':
        setpoint = Settings.get('ec_setpoint', 1350)
        buffer = Settings.get('ec_buffer', 150)
        min_val = setpoint - buffer
        max_val = setpoint + buffer
        
        if value < min_val:
            message = f"EC is low: {value:.0f} µS/cm (below {min_val:.0f})"
        elif value > max_val:
            message = f"EC is high: {value:.0f} µS/cm (above {max_val:.0f})"
            
    elif sensor_type == 'temp':
        # Use plant profile temperature ranges if available
        plant_profiles = Settings.get('plant_profiles', {})
        active_profile = Settings.get('active_plant_profile', 'general')
        
        if active_profile in plant_profiles:
            profile = plant_profiles[active_profile]
            min_val = profile.get('temp_min', 18.0)
            max_val = profile.get('temp_max', 28.0)
        else:
            # Fall back to alert thresholds
            min_val = Settings.get('temp_min_alert', 18.0)
            max_val = Settings.get('temp_max_alert', 30.0)
        
        if value < min_val:
            message = f"Temperature is low: {value:.1f}°C (below {min_val:.1f}°C)"
        elif value > max_val:
            message = f"Temperature is high: {value:.1f}°C (above {max_val:.1f}°C)"
    
    # Send notification if needed
    if message:
        from app.utils.notification_manager import notify_out_of_range
        notify_out_of_range(sensor_type, message)

def read_all_sensors():
    """Read all sensors and return the values"""
    results = {}
    for sensor_type in SENSOR_ADDRESSES.keys():
        try:
            results[sensor_type] = read_and_log_sensor(sensor_type)
        except Exception as e:
            logger.error(f"Error reading {sensor_type} sensor: {e}")
            results[sensor_type] = None
    return results

def get_last_reading(sensor_type, default=None):
    """Get the last reading for a sensor type from cache or database"""
    # Check cache first
    if sensor_type in last_readings and last_readings[sensor_type] is not None:
        return last_readings[sensor_type]
    
    # Fall back to database
    reading = SensorReading.get_latest(sensor_type)
    if reading:
        # Update cache
        last_readings[sensor_type] = reading.value
        return reading.value
    
    return default

def calibrate_ph(point, value):
    """Calibrate pH sensor with the specified point and value"""
    if point not in ['mid', 'low', 'high']:
        raise ValueError("pH calibration point must be 'mid', 'low', or 'high'")
    
    address = SENSOR_ADDRESSES['ph']
    
    # Map points to calibration types
    cal_map = {
        'mid': '7.00',
        'low': '4.00',
        'high': '10.00'
    }
    
    # If a specific value is provided, use it
    cal_value = value if value else cal_map[point]
    
    # Send calibration command
    send_command(address, f"{CALIBRATION_COMMAND},{point},{cal_value}")
    time.sleep(1.3)  # Wait for calibration
    
    # Read response
    response = read_response(address)
    
    if response.startswith('?'):
        raise Exception(f"Error calibrating pH sensor: {response}")
    
    return True

def calibrate_ec(point, value=None):
    """Calibrate EC sensor with the specified point and value"""
    if point not in ['dry', 'single', 'low', 'high']:
        raise ValueError("EC calibration point must be 'dry', 'single', 'low', or 'high'")
    
    address = SENSOR_ADDRESSES['ec']
    
    # Prepare calibration command
    if point == 'dry':
        cmd = f"{CALIBRATION_COMMAND},dry"
    elif value:
        cmd = f"{CALIBRATION_COMMAND},{point},{value}"
    else:
        raise ValueError("Value must be provided for EC calibration except for dry point")
    
    # Send calibration command
    send_command(address, cmd)
    time.sleep(1.3)  # Wait for calibration
    
    # Read response
    response = read_response(address)
    
    if response.startswith('?'):
        raise Exception(f"Error calibrating EC sensor: {response}")
    
    return True

def calibrate_temperature(value):
    """Calibrate temperature sensor with the specified value"""
    address = SENSOR_ADDRESSES['temp']
    
    # Send calibration command
    send_command(address, f"{CALIBRATION_COMMAND},{value}")
    time.sleep(1.3)  # Wait for calibration
    
    # Read response
    response = read_response(address)
    
    if response.startswith('?'):
        raise Exception(f"Error calibrating temperature sensor: {response}")
    
    return True 