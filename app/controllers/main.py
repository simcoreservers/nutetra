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
    
    # Get target ranges for the dashboard
    ph_setpoint = Settings.get('ph_setpoint', 6.0)
    ph_buffer = Settings.get('ph_buffer', 0.2)
    ph_min = ph_setpoint - ph_buffer
    ph_max = ph_setpoint + ph_buffer
    
    ec_setpoint = Settings.get('ec_setpoint', 1350)
    ec_buffer = Settings.get('ec_buffer', 150)
    ec_min = ec_setpoint - ec_buffer
    ec_max = ec_setpoint + ec_buffer
    
    # No temperature control
    
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
    
    # Get active plant profile information
    active_profile_id = Settings.get('active_plant_profile', 'general')
    plant_profiles = Settings.get('plant_profiles', {})
    active_profile = plant_profiles.get(active_profile_id, {})
    
    # Get growth phase for active profile
    growth_phase = None
    if active_profile and active_profile.get('weekly_schedules') and active_profile.get('current_week'):
        from app.controllers.garden import get_growth_phase_for_week
        growth_phase = get_growth_phase_for_week(active_profile, active_profile.get('current_week'))
    
    return render_template(
        'dashboard.html', 
        ph_reading=ph_reading,
        ec_reading=ec_reading,
        temp_reading=temp_reading,
        ph_min=ph_min,
        ph_max=ph_max,
        ec_min=ec_min,
        ec_max=ec_max,
        recent_events=recent_events,
        ph_chart_data=ph_chart_data,
        ec_chart_data=ec_chart_data,
        temp_chart_data=temp_chart_data,
        auto_dosing=auto_dosing,
        active_profile=active_profile,
        active_profile_id=active_profile_id,
        growth_phase=growth_phase
    )

@main_bp.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@main_bp.route('/documentation')
def documentation():
    """Render the documentation page"""
    return render_template('documentation.html') 