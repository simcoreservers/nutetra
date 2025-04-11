from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.pump import Pump
from app.models.dosing_event import DosingEvent
from app.models.settings import Settings
from app.utils.dosing_manager import activate_pump, schedule_dosing_checks
from app import db
import uuid
from datetime import datetime
import copy
from app.models.nutrient import NutrientBrand, NutrientProduct

# Create a blueprint
dosing_bp = Blueprint('dosing', __name__)

@dosing_bp.route('/')
def index():
    """Show dosing management page"""
    # Get all pumps
    pumps = Pump.query.all()
    
    # Get recent dosing events
    recent_events = DosingEvent.get_recent(10)
    
    # Get auto-dosing status
    auto_dosing = Settings.get('auto_dosing_enabled', True)
    
    return render_template(
        'hardware/index.html',
        pumps=pumps,
        recent_events=recent_events,
        auto_dosing=auto_dosing
    )

@dosing_bp.route('/pumps')
def pumps():
    """Show pump management page"""
    # Get all pumps
    pumps = Pump.query.all()
    
    return render_template(
        'hardware/pumps.html',
        pumps=pumps
    )

@dosing_bp.route('/pumps/add', methods=['GET', 'POST'])
def add_pump():
    """Add a new pump"""
    if request.method == 'POST':
        # Get pump details from form
        name = request.form.get('name')
        pump_type = request.form.get('type')
        gpio_pin = request.form.get('gpio_pin', type=int)
        flow_rate = request.form.get('flow_rate', type=float)
        
        # Validate input
        if not name or not pump_type or not gpio_pin or flow_rate is None:
            flash('All fields are required', 'error')
            return redirect(url_for('dosing.add_pump'))
        
        # Check if the GPIO pin is already in use
        existing_pump = Pump.query.filter_by(gpio_pin=gpio_pin).first()
        if existing_pump:
            flash(f'GPIO pin {gpio_pin} is already in use by pump "{existing_pump.name}"', 'error')
            return redirect(url_for('dosing.add_pump'))
        
        # Create the new pump
        new_pump = Pump(
            name=name,
            type=pump_type,
            gpio_pin=gpio_pin,
            flow_rate=flow_rate,
            enabled=True
        )
        
        # Save to database
        db.session.add(new_pump)
        db.session.commit()
        
        flash(f'Pump "{name}" added successfully', 'success')
        return redirect(url_for('dosing.pumps'))
    
    # For GET requests, show the add pump form
    pump_types = [
        {'value': 'ph_up', 'label': 'pH Up'},
        {'value': 'ph_down', 'label': 'pH Down'},
        {'value': 'nutrient_a', 'label': 'Nutrient A'},
        {'value': 'nutrient_b', 'label': 'Nutrient B'},
        {'value': 'nutrient_c', 'label': 'Nutrient C'},
        {'value': 'custom', 'label': 'Custom'}
    ]
    
    return render_template(
        'hardware/add_pump.html',
        pump_types=pump_types
    )

@dosing_bp.route('/pumps/edit/<int:pump_id>', methods=['GET', 'POST'])
def edit_pump(pump_id):
    """Edit an existing pump"""
    # Get the pump
    pump = Pump.query.get_or_404(pump_id)
    
    if request.method == 'POST':
        # Get pump details from form
        name = request.form.get('name')
        pump_type = request.form.get('type')
        gpio_pin = request.form.get('gpio_pin', type=int)
        flow_rate = request.form.get('flow_rate', type=float)
        enabled = 'enabled' in request.form
        
        # Validate input
        if not name or not pump_type or not gpio_pin or flow_rate is None:
            flash('All fields are required', 'error')
            return redirect(url_for('dosing.edit_pump', pump_id=pump_id))
        
        # Check if the GPIO pin is already in use by another pump
        existing_pump = Pump.query.filter_by(gpio_pin=gpio_pin).first()
        if existing_pump and existing_pump.id != pump_id:
            flash(f'GPIO pin {gpio_pin} is already in use by pump "{existing_pump.name}"', 'error')
            return redirect(url_for('dosing.edit_pump', pump_id=pump_id))
        
        # Update the pump
        pump.name = name
        pump.type = pump_type
        pump.gpio_pin = gpio_pin
        pump.flow_rate = flow_rate
        pump.enabled = enabled
        
        # Save to database
        db.session.commit()
        
        flash(f'Pump "{name}" updated successfully', 'success')
        return redirect(url_for('dosing.pumps'))
    
    # For GET requests, show the edit pump form
    pump_types = [
        {'value': 'ph_up', 'label': 'pH Up'},
        {'value': 'ph_down', 'label': 'pH Down'},
        {'value': 'nutrient_a', 'label': 'Nutrient A'},
        {'value': 'nutrient_b', 'label': 'Nutrient B'},
        {'value': 'nutrient_c', 'label': 'Nutrient C'},
        {'value': 'custom', 'label': 'Custom'}
    ]
    
    return render_template(
        'hardware/edit_pump.html',
        pump=pump,
        pump_types=pump_types
    )

@dosing_bp.route('/pumps/calibrate/<int:pump_id>', methods=['GET', 'POST'])
def calibrate_pump(pump_id):
    """Calibrate a pump's flow rate"""
    # Get the pump
    pump = Pump.query.get_or_404(pump_id)
    
    if request.method == 'POST':
        # Get calibration details from form
        duration_ms = request.form.get('duration_ms', type=int)
        measured_volume = request.form.get('measured_volume', type=float)
        
        # Validate input
        if not duration_ms or not measured_volume:
            flash('All fields are required', 'error')
            return redirect(url_for('dosing.calibrate_pump', pump_id=pump_id))
        
        # Calculate new flow rate (ml/s)
        flow_rate = measured_volume / (duration_ms / 1000)
        
        # Update the pump
        pump.flow_rate = flow_rate
        
        # Save to database
        db.session.commit()
        
        flash(f'Pump "{pump.name}" calibrated successfully. New flow rate: {flow_rate:.2f} ml/s', 'success')
        return redirect(url_for('dosing.pumps'))
    
    # For GET requests, show the calibration form
    return render_template(
        'hardware/calibrate_pump.html',
        pump=pump
    )

@dosing_bp.route('/pumps/test/<int:pump_id>', methods=['POST'])
def test_pump(pump_id):
    """Test a pump by running it for a short time"""
    try:
        # Get parameters from request
        data = request.get_json() or {}
        duration_ms = data.get('duration_ms', 1000)  # Default to 1 second
        
        # Activate the pump
        success = activate_pump(
            pump_id=pump_id,
            duration_ms=int(duration_ms),
            reason='test'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Pump test completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to activate pump'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dosing_bp.route('/events')
def events():
    """Show dosing events history"""
    # Get all events or filter by pump
    pump_id = request.args.get('pump_id', type=int)
    
    if pump_id:
        # Get events for a specific pump
        events = DosingEvent.get_for_pump(pump_id, 100)
        pump = Pump.query.get(pump_id)
        title = f'Dosing Events for {pump.name if pump else "Unknown Pump"}'
    else:
        # Get all recent events
        events = DosingEvent.get_recent(100)
        title = 'Recent Dosing Events'
    
    # Get all pumps for the filter dropdown
    pumps = Pump.query.all()
    
    return render_template(
        'hardware/events.html',
        events=events,
        pumps=pumps,
        selected_pump_id=pump_id,
        title=title
    )

@dosing_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Manage dosing settings"""
    if request.method == 'POST':
        # Update settings from form
        auto_dosing = 'auto_dosing_enabled' in request.form
        night_mode = 'night_mode_enabled' in request.form
        
        # pH settings
        ph_setpoint = request.form.get('ph_setpoint', type=float)
        ph_buffer = request.form.get('ph_buffer', type=float)
        ph_dose = request.form.get('ph_dose_amount', type=float)
        ph_interval = request.form.get('ph_check_interval', type=int)
        ph_wait = request.form.get('ph_dose_wait_time', type=int)
        
        # EC settings
        ec_setpoint = request.form.get('ec_setpoint', type=float)
        ec_buffer = request.form.get('ec_buffer', type=float)
        ec_dose = request.form.get('ec_dose_amount', type=float)
        ec_interval = request.form.get('ec_check_interval', type=int)
        ec_wait = request.form.get('ec_dose_wait_time', type=int)
        
        # Night mode settings
        night_start = request.form.get('night_mode_start')
        night_end = request.form.get('night_mode_end')
        
        # Update settings
        Settings.set('auto_dosing_enabled', auto_dosing)
        Settings.set('night_mode_enabled', night_mode)
        
        # pH settings
        Settings.set('ph_setpoint', ph_setpoint)
        Settings.set('ph_buffer', ph_buffer)
        Settings.set('ph_dose_amount', ph_dose)
        Settings.set('ph_check_interval', ph_interval)
        Settings.set('ph_dose_wait_time', ph_wait)
        
        # EC settings
        Settings.set('ec_setpoint', ec_setpoint)
        Settings.set('ec_buffer', ec_buffer)
        Settings.set('ec_dose_amount', ec_dose)
        Settings.set('ec_check_interval', ec_interval)
        Settings.set('ec_dose_wait_time', ec_wait)
        
        # Night mode settings
        Settings.set('night_mode_start', night_start)
        Settings.set('night_mode_end', night_end)
        
        # Reschedule checks with new intervals
        schedule_dosing_checks()
        
        flash('Dosing settings updated successfully', 'success')
        return redirect(url_for('dosing.settings'))
    
    # For GET requests, show the settings form
    
    # Get current settings
    settings = {
        'auto_dosing_enabled': Settings.get('auto_dosing_enabled', True),
        'night_mode_enabled': Settings.get('night_mode_enabled', False),
        
        # pH settings
        'ph_setpoint': Settings.get('ph_setpoint', 6.0),
        'ph_buffer': Settings.get('ph_buffer', 0.2),
        'ph_dose_amount': Settings.get('ph_dose_amount', 1.0),
        'ph_check_interval': Settings.get('ph_check_interval', 60),
        'ph_dose_wait_time': Settings.get('ph_dose_wait_time', 10),
        
        # EC settings
        'ec_setpoint': Settings.get('ec_setpoint', 1350),
        'ec_buffer': Settings.get('ec_buffer', 150),
        'ec_dose_amount': Settings.get('ec_dose_amount', 5.0),
        'ec_check_interval': Settings.get('ec_check_interval', 120),
        'ec_dose_wait_time': Settings.get('ec_dose_wait_time', 30),
        
        # Night mode settings
        'night_mode_start': Settings.get('night_mode_start', '22:00'),
        'night_mode_end': Settings.get('night_mode_end', '06:00')
    }
    
    return render_template(
        'hardware/settings.html',
        settings=settings
    )

# Note: The following routes have been moved to the garden blueprint:
# - /profiles and all sub-routes (/profiles/add, /profiles/edit, etc.)
# - /nutrients
# - /grow-cycle
# - /profiles/activate
# - /profile_form
# These routes should be accessed via the /garden URL prefix now 