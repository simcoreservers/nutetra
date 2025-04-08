from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.sensor_reading import SensorReading
from app.models.settings import Settings
from app.utils.sensor_manager import calibrate_ph, calibrate_ec, calibrate_temperature
from app.utils.notification_manager import notify_out_of_range
import json

# Create a blueprint
sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/')
def index():
    """Show sensor overview and management page"""
    # Get latest readings
    ph_reading = SensorReading.get_latest('ph')
    ec_reading = SensorReading.get_latest('ec')
    temp_reading = SensorReading.get_latest('temp')
    
    # Get target ranges using setpoint and buffer
    ph_setpoint = Settings.get('ph_setpoint', 6.0)
    ph_buffer = Settings.get('ph_buffer', 0.2)
    ph_min = ph_setpoint - ph_buffer
    ph_max = ph_setpoint + ph_buffer
    
    ec_setpoint = Settings.get('ec_setpoint', 1350)
    ec_buffer = Settings.get('ec_buffer', 150)
    ec_min = ec_setpoint - ec_buffer
    ec_max = ec_setpoint + ec_buffer
    
    # No temperature control, so no min/max
    
    # Prepare status messages
    ph_status = "Normal"
    ec_status = "Normal"
    temp_status = "Normal"
    
    # Check if readings are out of range
    if ph_reading:
        if ph_reading.value < ph_min:
            ph_status = "Low"
        elif ph_reading.value > ph_max:
            ph_status = "High"
    
    if ec_reading:
        if ec_reading.value < ec_min:
            ec_status = "Low"
        elif ec_reading.value > ec_max:
            ec_status = "High"
    
    if temp_reading:
        # No target ranges for temperature, just display the reading
        temp_status = "Monitoring"
    
    return render_template(
        'sensors/index.html',
        ph_reading=ph_reading.value if ph_reading else None,
        ec_reading=ec_reading.value if ec_reading else None,
        temp_reading=temp_reading.value if temp_reading else None,
        ph_min=ph_min,
        ph_max=ph_max,
        ec_min=ec_min,
        ec_max=ec_max,
        temp_min=temp_min,
        temp_max=temp_max,
        ph_status=ph_status,
        ec_status=ec_status,
        temp_status=temp_status
    )

@sensors_bp.route('/history')
def history():
    """Show sensor history and charts"""
    # Get historical data
    ph_history = SensorReading.get_history('ph', 100)
    ec_history = SensorReading.get_history('ec', 100)
    temp_history = SensorReading.get_history('temp', 100)
    
    # Format data for charts
    ph_data = []
    ec_data = []
    temp_data = []
    
    for reading in ph_history:
        ph_data.append({
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        })
    
    for reading in ec_history:
        ec_data.append({
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        })
    
    for reading in temp_history:
        temp_data.append({
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        })
    
    # Get target ranges for chart display
    ph_setpoint = Settings.get('ph_setpoint', 6.0)
    ph_buffer = Settings.get('ph_buffer', 0.2)
    ph_min = ph_setpoint - ph_buffer
    ph_max = ph_setpoint + ph_buffer
    
    ec_setpoint = Settings.get('ec_setpoint', 1350)
    ec_buffer = Settings.get('ec_buffer', 150)
    ec_min = ec_setpoint - ec_buffer
    ec_max = ec_setpoint + ec_buffer
    
    # No temperature control ranges
    
    return render_template(
        'sensors/history.html',
        ph_data=json.dumps(ph_data),
        ec_data=json.dumps(ec_data),
        temp_data=json.dumps(temp_data),
        ph_min=ph_min,
        ph_max=ph_max,
        ec_min=ec_min,
        ec_max=ec_max
    )

@sensors_bp.route('/calibration')
def calibration():
    """Show sensor calibration page"""
    return render_template('sensors/calibration.html')

@sensors_bp.route('/calibration/ph', methods=['POST'])
def calibrate_ph_sensor():
    """Calibrate pH sensor"""
    point = request.form.get('point')
    value = request.form.get('value')
    
    if not point:
        flash('Calibration point must be specified', 'error')
        return redirect(url_for('sensors.calibration'))
    
    try:
        # Perform calibration
        calibrate_ph(point, value)
        flash(f'pH sensor calibrated successfully at {point} point', 'success')
    except Exception as e:
        flash(f'Calibration failed: {str(e)}', 'error')
    
    return redirect(url_for('sensors.calibration'))

@sensors_bp.route('/calibration/ec', methods=['POST'])
def calibrate_ec_sensor():
    """Calibrate EC sensor"""
    point = request.form.get('point')
    value = request.form.get('value')
    
    if not point:
        flash('Calibration point must be specified', 'error')
        return redirect(url_for('sensors.calibration'))
    
    try:
        # Perform calibration
        calibrate_ec(point, value)
        flash(f'EC sensor calibrated successfully at {point} point', 'success')
    except Exception as e:
        flash(f'Calibration failed: {str(e)}', 'error')
    
    return redirect(url_for('sensors.calibration'))

@sensors_bp.route('/calibration/temperature', methods=['POST'])
def calibrate_temp_sensor():
    """Calibrate temperature sensor"""
    value = request.form.get('value')
    
    if not value:
        flash('Calibration value must be specified', 'error')
        return redirect(url_for('sensors.calibration'))
    
    try:
        # Perform calibration
        calibrate_temperature(float(value))
        flash(f'Temperature sensor calibrated successfully to {value}°C', 'success')
    except Exception as e:
        flash(f'Calibration failed: {str(e)}', 'error')
    
    return redirect(url_for('sensors.calibration'))

@sensors_bp.route('/check-ranges', methods=['POST'])
def check_ranges():
    """Check if sensor readings are within range and send notifications if needed"""
    try:
        # Get latest readings
        ph_reading = SensorReading.get_latest('ph')
        ec_reading = SensorReading.get_latest('ec')
        temp_reading = SensorReading.get_latest('temp')
        
        # Get target ranges using setpoint and buffer
        ph_setpoint = Settings.get('ph_setpoint', 6.0)
        ph_buffer = Settings.get('ph_buffer', 0.2)
        ph_min = ph_setpoint - ph_buffer
        ph_max = ph_setpoint + ph_buffer
        
        ec_setpoint = Settings.get('ec_setpoint', 1350)
        ec_buffer = Settings.get('ec_buffer', 150)
        ec_min = ec_setpoint - ec_buffer
        ec_max = ec_setpoint + ec_buffer
        
        notifications_sent = []
        
        # Check pH
        if ph_reading and (ph_reading.value < ph_min or ph_reading.value > ph_max):
            notify_out_of_range('ph', ph_reading.value, ph_min, ph_max)
            notifications_sent.append('pH')
        
        # Check EC
        if ec_reading and (ec_reading.value < ec_min or ec_reading.value > ec_max):
            notify_out_of_range('ec', ec_reading.value, ec_min, ec_max)
            notifications_sent.append('EC')
        
        # Check temperature
        if temp_reading and (temp_reading.value < temp_min or temp_reading.value > temp_max):
            notify_out_of_range('temp', temp_reading.value, temp_min, temp_max)
            notifications_sent.append('Temperature')
        
        if notifications_sent:
            return jsonify({
                'success': True,
                'message': f"Notifications sent for out-of-range readings: {', '.join(notifications_sent)}"
            })
        else:
            return jsonify({
                'success': True,
                'message': "All readings are within range"
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 