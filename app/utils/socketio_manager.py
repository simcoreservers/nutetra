"""
Socket.IO Manager for NuTetra Controller
Handles real-time updates for sensor data and notifications
"""

from flask_socketio import SocketIO
from flask import current_app
import time
import threading
import logging

# Global variables for thread management
broadcast_thread = None
thread_stop_event = threading.Event()
app = None

def init_socketio(flask_app):
    """
    Initialize Socket.IO with the Flask app
    Returns the socketio instance for use in the app
    """
    global app
    app = flask_app
    
    # Create a new SocketIO instance
    socketio_instance = SocketIO(app, cors_allowed_origins="*")
    
    # Register event handlers
    register_handlers(socketio_instance)
    
    # Start the background thread for sensor updates
    start_background_thread(socketio_instance)
    
    return socketio_instance

def register_handlers(socketio_instance):
    """
    Register Socket.IO event handlers
    """
    @socketio_instance.on('connect')
    def handle_connect():
        logging.info('Client connected to Socket.IO')
    
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        logging.info('Client disconnected from Socket.IO')
    
    @socketio_instance.on('subscribe')
    def handle_subscribe(data):
        """
        Handle client subscription to different channels
        """
        channel = data.get('channel')
        if not channel:
            return
        
        # Join the requested channel room
        from flask_socketio import join_room
        join_room(channel)
        logging.info(f'Client subscribed to channel: {channel}')

def start_background_thread(socketio_instance):
    """
    Start background thread for broadcasting sensor updates
    """
    global broadcast_thread, thread_stop_event
    
    if broadcast_thread is None or not broadcast_thread.is_alive():
        thread_stop_event.clear()
        broadcast_thread = threading.Thread(
            target=background_broadcaster,
            args=(socketio_instance,)
        )
        broadcast_thread.daemon = True
        broadcast_thread.start()
        logging.info('Started Socket.IO background broadcast thread')

def stop_background_thread():
    """
    Stop the background broadcasting thread
    """
    global thread_stop_event
    thread_stop_event.set()
    logging.info('Stopping Socket.IO background broadcast thread')

def background_broadcaster(socketio_instance):
    """
    Background thread function that sends sensor updates periodically
    """
    global app
    with app.app_context():
        from ..models.settings import Settings
        from ..models.sensor import SensorData
        
        while not thread_stop_event.is_set():
            try:
                # Get refresh interval from settings
                refresh_interval = Settings.get('refresh_interval', 10)
                
                # Get latest sensor data
                sensor_data = SensorData.get_latest()
                
                if sensor_data:
                    # Broadcast update to clients
                    emit_sensor_update(socketio_instance, sensor_data)
                
                # Sleep for the refresh interval
                time.sleep(refresh_interval)
            except Exception as e:
                logging.error(f'Error in Socket.IO broadcaster: {e}')
                time.sleep(10)  # Sleep on error to prevent high CPU usage

def emit_sensor_update(socketio_instance, sensor_data):
    """
    Emit sensor update to connected clients
    """
    if not socketio_instance or not sensor_data:
        return
    
    # Prepare data
    data = {
        'ph': sensor_data.ph,
        'ec': sensor_data.ec,
        'temp': sensor_data.temperature,
        'timestamp': sensor_data.timestamp.isoformat(),
        'sensor_status': {
            'ph': 'disconnected' if sensor_data.ph is None else 'connected',
            'ec': 'disconnected' if sensor_data.ec is None else 'connected',
            'temp': 'disconnected' if sensor_data.temperature is None else 'connected'
        }
    }
    
    # Emit to the sensor channel
    socketio_instance.emit('sensor_update', data, room='sensors')

def emit_notification(socketio_instance, notification):
    """
    Emit a new notification to connected clients
    """
    if not socketio_instance or not notification:
        return
    
    # Prepare data
    data = {
        'id': notification.id,
        'message': notification.message,
        'type': notification.type,
        'timestamp': notification.timestamp.isoformat(),
        'is_read': notification.is_read
    }
    
    # Emit to the notifications channel
    socketio_instance.emit('new_notification', data, room='notifications')

def emit_dosing_event(socketio_instance, pump, amount_ml):
    """
    Emit a dosing event to connected clients
    """
    if not socketio_instance or not pump:
        return
    
    # Prepare data
    data = {
        'pump_id': pump.id,
        'pump_name': pump.name,
        'amount_ml': amount_ml,
        'timestamp': time.time() * 1000,  # Unix timestamp in ms
    }
    
    # Emit to the dosing channel
    socketio_instance.emit('dosing_event', data, room='dosing')

def emit_system_alert(socketio_instance, message, level='info'):
    """
    Emit a system alert to connected clients
    """
    if not socketio_instance:
        return
    
    # Prepare data
    data = {
        'message': message,
        'level': level,  # 'info', 'warning', 'error', 'success'
        'timestamp': time.time() * 1000,  # Unix timestamp in ms
    }
    
    # Emit to the system channel
    socketio_instance.emit('system_alert', data, room='system') 