from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.settings import Settings
from app.utils.notification_manager import send_notification
from app import db
import os
import json

# Create a blueprint
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
def index():
    """Show main settings page"""
    return render_template('settings/index.html')

@settings_bp.route('/system', methods=['GET', 'POST'])
def system():
    """Manage system settings"""
    if request.method == 'POST':
        # Get values from form
        dark_mode = 'dark_mode' in request.form
        refresh_interval = request.form.get('refresh_interval', type=int)
        chart_points = request.form.get('chart_points', type=int)
        logging_interval = request.form.get('logging_interval', type=int)
        
        # Update settings
        Settings.set('dark_mode', dark_mode)
        
        if refresh_interval is not None:
            Settings.set('refresh_interval', refresh_interval)
        
        if chart_points is not None:
            Settings.set('chart_points', chart_points)
        
        if logging_interval is not None:
            Settings.set('logging_interval', logging_interval)
        
        flash('System settings updated successfully', 'success')
        return redirect(url_for('settings.system'))
    
    # Get current settings for display
    settings = {
        'dark_mode': Settings.get('dark_mode', True),
        'refresh_interval': Settings.get('refresh_interval', 10),
        'chart_points': Settings.get('chart_points', 50),
        'logging_interval': Settings.get('logging_interval', 300)
    }
    
    return render_template(
        'settings/system.html',
        settings=settings
    )

@settings_bp.route('/notifications', methods=['GET', 'POST'])
def notifications():
    """Manage notification settings"""
    if request.method == 'POST':
        # Get values from form
        notifications_enabled = 'notifications_enabled' in request.form
        email_notifications = 'email_notifications' in request.form
        sms_notifications = 'sms_notifications' in request.form
        
        email_address = request.form.get('email_address')
        email_password = request.form.get('email_password')
        email_smtp_server = request.form.get('email_smtp_server')
        email_smtp_port = request.form.get('email_smtp_port', type=int)
        
        phone_number = request.form.get('phone_number')
        sms_service = request.form.get('sms_service')
        sms_api_key = request.form.get('sms_api_key')
        
        # Additional Twilio settings
        twilio_account_sid = request.form.get('twilio_account_sid')
        twilio_auth_token = request.form.get('twilio_auth_token')
        twilio_phone_number = request.form.get('twilio_phone_number')
        
        # Update basic settings
        Settings.set('notifications_enabled', notifications_enabled)
        Settings.set('email_notifications', email_notifications)
        Settings.set('sms_notifications', sms_notifications)
        
        # Update email settings if provided
        if email_address:
            Settings.set('email_address', email_address)
        
        # Only update password if provided (don't overwrite with empty)
        if email_password:
            Settings.set('email_password', email_password)
        
        if email_smtp_server:
            Settings.set('email_smtp_server', email_smtp_server)
        
        if email_smtp_port:
            Settings.set('email_smtp_port', email_smtp_port)
        
        # Update SMS settings if provided
        if phone_number:
            Settings.set('phone_number', phone_number)
        
        if sms_service:
            Settings.set('sms_service', sms_service)
        
        if sms_api_key:
            Settings.set('sms_api_key', sms_api_key)
        
        # Update Twilio settings if provided
        if twilio_account_sid:
            Settings.set('twilio_account_sid', twilio_account_sid)
        
        if twilio_auth_token:
            Settings.set('twilio_auth_token', twilio_auth_token)
        
        if twilio_phone_number:
            Settings.set('twilio_phone_number', twilio_phone_number)
        
        flash('Notification settings updated successfully', 'success')
        return redirect(url_for('settings.notifications'))
    
    # Get current settings for display
    settings = {
        'notifications_enabled': Settings.get('notifications_enabled', True),
        'email_notifications': Settings.get('email_notifications', False),
        'email_address': Settings.get('email_address', ''),
        'email_smtp_server': Settings.get('email_smtp_server', 'smtp.gmail.com'),
        'email_smtp_port': Settings.get('email_smtp_port', 587),
        'sms_notifications': Settings.get('sms_notifications', False),
        'phone_number': Settings.get('phone_number', ''),
        'sms_service': Settings.get('sms_service', 'twilio'),
        'twilio_account_sid': Settings.get('twilio_account_sid', ''),
        'twilio_phone_number': Settings.get('twilio_phone_number', '')
    }
    
    # Mask secrets (auth token, API key)
    sms_api_key = Settings.get('sms_api_key', '')
    settings['sms_api_key_set'] = bool(sms_api_key)
    
    twilio_auth_token = Settings.get('twilio_auth_token', '')
    settings['twilio_auth_token_set'] = bool(twilio_auth_token)
    
    email_password = Settings.get('email_password', '')
    settings['email_password_set'] = bool(email_password)
    
    return render_template(
        'settings/notifications.html',
        settings=settings
    )

@settings_bp.route('/test_notification', methods=['POST'])
def test_notification():
    """Send a test notification"""
    try:
        # Get notification type
        notification_type = request.form.get('type', 'all')
        
        if notification_type == 'email' or notification_type == 'all':
            # Test email notification
            if Settings.get('email_notifications', False):
                send_notification(
                    subject="Test Email Notification",
                    message="This is a test notification from your NuTetra Controller.",
                    level="info"
                )
        
        if notification_type == 'sms' or notification_type == 'all':
            # Test SMS notification
            if Settings.get('sms_notifications', False):
                send_notification(
                    subject="Test SMS",
                    message="This is a test SMS from your NuTetra Controller.",
                    level="info"
                )
        
        flash('Test notification sent successfully', 'success')
    except Exception as e:
        flash(f'Error sending test notification: {str(e)}', 'error')
    
    return redirect(url_for('settings.notifications'))

@settings_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    """Backup and restore system settings"""
    if request.method == 'POST':
        # Check if this is a restore operation
        if 'restore_file' in request.files:
            restore_file = request.files['restore_file']
            
            if restore_file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('settings.backup'))
            
            try:
                # Read and parse the backup file
                backup_data = json.loads(restore_file.read().decode('utf-8'))
                
                # Restore settings
                if 'settings' in backup_data:
                    for key, value in backup_data['settings'].items():
                        Settings.set(key, value)
                
                # Restore pumps
                if 'pumps' in backup_data:
                    from app.models.pump import Pump
                    
                    # Clear existing pumps
                    Pump.query.delete()
                    
                    # Add pumps from backup
                    for pump_data in backup_data['pumps']:
                        pump = Pump(
                            name=pump_data['name'],
                            type=pump_data['type'],
                            gpio_pin=pump_data['gpio_pin'],
                            flow_rate=pump_data['flow_rate'],
                            enabled=pump_data.get('enabled', True)
                        )
                        db.session.add(pump)
                
                db.session.commit()
                flash('System restored successfully from backup', 'success')
            except Exception as e:
                flash(f'Error restoring from backup: {str(e)}', 'error')
            
            return redirect(url_for('settings.backup'))
    
    # Create backup data for download
    from app.models.pump import Pump
    
    backup_data = {
        'settings': Settings.get_all(),
        'pumps': [pump.to_dict() for pump in Pump.query.all()]
    }
    
    # Generate a timestamp for the backup filename
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"nutetra_backup_{timestamp}.json"
    
    return render_template(
        'settings/backup.html',
        backup_data=json.dumps(backup_data, indent=2),
        backup_filename=backup_filename
    )

@settings_bp.route('/reset', methods=['POST'])
def reset():
    """Reset the system to default settings"""
    try:
        # Get the reset type
        reset_type = request.form.get('reset_type')
        
        if reset_type == 'settings':
            # Reset all settings to defaults
            Settings.query.delete()
            db.session.commit()
            
            # Re-initialize default settings
            Settings.initialize_defaults()
            
            flash('Settings reset to defaults successfully', 'success')
        
        elif reset_type == 'pumps':
            # Reset all pumps to defaults
            from app.models.pump import Pump
            Pump.query.delete()
            db.session.commit()
            
            # Re-initialize default pumps
            Pump.initialize_defaults()
            
            flash('Pumps reset to defaults successfully', 'success')
        
        elif reset_type == 'all':
            # Reset everything
            from app.models.sensor_reading import SensorReading
            from app.models.dosing_event import DosingEvent
            from app.models.pump import Pump
            
            # Delete all data
            SensorReading.query.delete()
            DosingEvent.query.delete()
            Pump.query.delete()
            Settings.query.delete()
            db.session.commit()
            
            # Re-initialize defaults
            Settings.initialize_defaults()
            Pump.initialize_defaults()
            
            flash('System reset to defaults successfully', 'success')
        
        else:
            flash('Invalid reset type', 'error')
    
    except Exception as e:
        flash(f'Error resetting system: {str(e)}', 'error')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/diagnostics')
def diagnostics():
    """Show system diagnostics information"""
    # Collect system information
    import platform
    import psutil
    
    try:
        # System info
        system_info = {
            'os': platform.platform(),
            'python': platform.python_version(),
            'hostname': platform.node()
        }
        
        # Hardware info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        hardware_info = {
            'cpu_percent': cpu_percent,
            'memory_total': f"{memory.total / (1024**3):.2f} GB",
            'memory_used': f"{memory.used / (1024**3):.2f} GB",
            'memory_percent': memory_percent,
            'disk_total': f"{disk.total / (1024**3):.2f} GB",
            'disk_used': f"{disk.used / (1024**3):.2f} GB",
            'disk_percent': disk_percent
        }
        
        # I2C device scan (check sensor connectivity)
        import smbus2
        i2c_devices = []
        try:
            bus = smbus2.SMBus(1)
            for address in range(0x03, 0x78):
                try:
                    bus.read_byte(address)
                    i2c_devices.append(f"0x{address:02X}")
                except:
                    pass
        except:
            i2c_devices = ["I2C bus not accessible"]
        
        # Get sensor status
        from app.utils.sensor_manager import SENSOR_ADDRESSES
        sensor_status = {}
        for sensor_type, address in SENSOR_ADDRESSES.items():
            hex_address = f"0x{address:02X}"
            sensor_status[sensor_type] = {
                'address': hex_address,
                'connected': hex_address in i2c_devices,
                'last_reading': None
            }
            
            # Get last reading
            from app.models.sensor_reading import SensorReading
            last_reading = SensorReading.get_latest(sensor_type)
            if last_reading:
                sensor_status[sensor_type]['last_reading'] = {
                    'value': last_reading.value,
                    'timestamp': last_reading.timestamp.isoformat()
                }
        
        # Get database stats
        db_stats = {
            'sensor_readings': SensorReading.query.count(),
            'dosing_events': DosingEvent.query.count(),
            'settings': Settings.query.count(),
            'pumps': Pump.query.count()
        }
        
        return render_template(
            'settings/diagnostics.html',
            system_info=system_info,
            hardware_info=hardware_info,
            i2c_devices=i2c_devices,
            sensor_status=sensor_status,
            db_stats=db_stats
        )
    except Exception as e:
        error_message = str(e)
        return render_template(
            'settings/diagnostics.html',
            error=error_message
        ) 