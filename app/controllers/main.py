from flask import Blueprint, render_template, redirect, url_for
from app.models.sensor_reading import SensorReading
from app.models.dosing_event import DosingEvent
from app.models.settings import Settings
from app.utils.sensor_manager import get_last_reading
import json

# Create a blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the main dashboard"""
    # Get latest sensor readings
    ph_reading = get_last_reading('ph')
    ec_reading = get_last_reading('ec')
    temp_reading = get_last_reading('temp')
    
    # Get recent dosing events
    recent_events = DosingEvent.get_recent(10)
    
    # Get target ranges
    ph_min = Settings.get('ph_target_min', 5.8)
    ph_max = Settings.get('ph_target_max', 6.2)
    ec_min = Settings.get('ec_target_min', 1.2)
    ec_max = Settings.get('ec_target_max', 1.5)
    temp_min = Settings.get('temp_target_min', 18.0)
    temp_max = Settings.get('temp_target_max', 24.0)
    
    # Get historical data for charts
    ph_history = SensorReading.get_history('ph', 50)
    ec_history = SensorReading.get_history('ec', 50)
    temp_history = SensorReading.get_history('temp', 50)
    
    # Format data for charts
    ph_chart_data = json.dumps([
        {
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        } for reading in ph_history
    ])
    
    ec_chart_data = json.dumps([
        {
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        } for reading in ec_history
    ])
    
    temp_chart_data = json.dumps([
        {
            'time': reading.timestamp.isoformat(),
            'value': reading.value
        } for reading in temp_history
    ])
    
    # Get auto-dosing status
    auto_dosing = Settings.get('auto_dosing_enabled', True)
    
    return render_template(
        'dashboard.html', 
        ph_reading=ph_reading,
        ec_reading=ec_reading,
        temp_reading=temp_reading,
        ph_min=ph_min,
        ph_max=ph_max,
        ec_min=ec_min,
        ec_max=ec_max,
        temp_min=temp_min,
        temp_max=temp_max,
        recent_events=recent_events,
        ph_chart_data=ph_chart_data,
        ec_chart_data=ec_chart_data,
        temp_chart_data=temp_chart_data,
        auto_dosing=auto_dosing
    )

@main_bp.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@main_bp.route('/documentation')
def documentation():
    """Render the documentation page"""
    return render_template('documentation.html') 