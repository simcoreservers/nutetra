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
        'dosing/index.html',
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
        'dosing/pumps.html',
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
        'dosing/add_pump.html',
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
        'dosing/edit_pump.html',
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
        'dosing/calibrate_pump.html',
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
        'dosing/events.html',
        events=events,
        pumps=pumps,
        selected_pump_id=pump_id,
        title=title
    )

@dosing_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Manage dosing settings"""
    # Ensure plant profiles are initialized
    if not Settings.get('plant_profiles'):
        # Use the Settings model to initialize default plant profiles
        Settings.initialize_defaults()
    
    # Auto-configure nutrient components based on available pumps
    # This updates default profiles with the user's actual enabled pumps
    config_result = Settings.auto_configure_nutrient_components()
    
    # Show configuration result as a message
    if config_result and "Updated" in config_result:
        flash(f"Plant profiles updated: {config_result}", 'success')
    
    if request.method == 'POST':
        # Update settings from form
        auto_dosing = 'auto_dosing_enabled' in request.form
        night_mode = 'night_mode_enabled' in request.form
        
        # Get plant profile selection
        active_profile = request.form.get('active_plant_profile')
        
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
        
        # Update active plant profile if changed
        if active_profile:
            Settings.set('active_plant_profile', active_profile)
            
            # If a profile was selected, apply its values as defaults
            plant_profiles = Settings.get('plant_profiles', {})
            if active_profile in plant_profiles:
                profile = plant_profiles[active_profile]
                
                # Apply profile setpoints if form values match previous defaults
                # (this means user didn't manually change them)
                current_ph = Settings.get('ph_setpoint')
                current_ec = Settings.get('ec_setpoint')
                
                if ph_setpoint is None or ph_setpoint == current_ph:
                    ph_setpoint = profile['ph_setpoint']
                
                if ph_buffer is None or ph_buffer == Settings.get('ph_buffer'):
                    ph_buffer = profile['ph_buffer']
                    
                if ec_setpoint is None or ec_setpoint == current_ec:
                    ec_setpoint = profile['ec_setpoint']
                
                if ec_buffer is None or ec_buffer == Settings.get('ec_buffer'):
                    ec_buffer = profile['ec_buffer']
        
        if ph_setpoint is not None:
            Settings.set('ph_setpoint', ph_setpoint)
        if ph_buffer is not None:
            Settings.set('ph_buffer', ph_buffer)
        if ph_dose is not None:
            Settings.set('ph_dose_amount', ph_dose)
        if ph_interval is not None:
            Settings.set('ph_check_interval', ph_interval)
        if ph_wait is not None:
            Settings.set('ph_dose_wait_time', ph_wait)
        
        if ec_setpoint is not None:
            Settings.set('ec_setpoint', ec_setpoint)
        if ec_buffer is not None:
            Settings.set('ec_buffer', ec_buffer)
        if ec_dose is not None:
            Settings.set('ec_dose_amount', ec_dose)
        if ec_interval is not None:
            Settings.set('ec_check_interval', ec_interval)
        if ec_wait is not None:
            Settings.set('ec_dose_wait_time', ec_wait)
        
        if night_start:
            Settings.set('night_mode_start', night_start)
        if night_end:
            Settings.set('night_mode_end', night_end)
        
        # Reschedule dosing checks with new settings
        schedule_dosing_checks()
        
        flash('Dosing settings updated successfully', 'success')
        return redirect(url_for('dosing.settings'))
    
    # For GET requests, show the settings form with current values
    settings = {
        'auto_dosing_enabled': Settings.get('auto_dosing_enabled', True),
        'night_mode_enabled': Settings.get('night_mode_enabled', False),
        'ph_setpoint': Settings.get('ph_setpoint', 6.0),
        'ph_buffer': Settings.get('ph_buffer', 0.2),
        'ph_dose_amount': Settings.get('ph_dose_amount', 1.0),
        'ph_check_interval': Settings.get('ph_check_interval', 300),
        'ph_dose_wait_time': Settings.get('ph_dose_wait_time', 60),
        'ec_setpoint': Settings.get('ec_setpoint', 1350),
        'ec_buffer': Settings.get('ec_buffer', 150),
        'ec_dose_amount': Settings.get('ec_dose_amount', 5.0),
        'ec_check_interval': Settings.get('ec_check_interval', 300),
        'ec_dose_wait_time': Settings.get('ec_dose_wait_time', 60),
        'night_mode_start': Settings.get('night_mode_start', '22:00'),
        'night_mode_end': Settings.get('night_mode_end', '06:00'),
        'active_plant_profile': Settings.get('active_plant_profile', 'general'),
        'plant_profiles': Settings.get('plant_profiles', {})
    }
    
    return render_template(
        'dosing/settings.html',
        settings=settings
    )

@dosing_bp.route('/profiles')
def manage_profiles():
    """Manage plant profiles"""
    # Auto-configure nutrient components based on available pumps
    # This ensures the default profiles are always up-to-date with available nutrients
    config_result = Settings.auto_configure_nutrient_components()
    
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Get the default profiles (these can't be deleted)
    default_profiles = ['general', 'leafy_greens', 'fruiting', 'herbs', 'strawberries']
    
    # Get all nutrient pumps to display information about them
    nutrient_pumps = Pump.query.filter(Pump.type == 'nutrient', Pump.enabled == True).all()
    
    # Show configuration result as a message
    if config_result and "Updated" in config_result:
        flash(f"Plant profiles updated: {config_result}", 'success')
    
    # Always show a message about pump configuration
    flash(f"Nutrient profile configuration: Found {len(nutrient_pumps)} active nutrient pumps. Ordered as: (1) Cal-Mag → (2) Micro → (3) Grow → (4) Bloom", 'info')
    
    return render_template(
        'dosing/profiles.html',
        profiles=plant_profiles,
        default_profiles=default_profiles,
        has_incompatibilities=False  # Simplified since we don't track incompatibilities anymore
    )

@dosing_bp.route('/profiles/reconfigure', methods=['POST'])
def reconfigure_profiles():
    """Force reconfiguration of all nutrient components in plant profiles"""
    # First, get all existing profiles to keep track of their custom status
    existing_profiles = Settings.get('plant_profiles', {})
    
    # Force reset of default nutrient ratios in the profiles
    Settings.initialize_defaults(force_reset=True)
    
    # Now auto-configure the components based on available pumps
    result = Settings.auto_configure_nutrient_components()
    
    # Show result message
    flash(f"All plant profiles have been reconfigured with proper nutrient ratios. {result}", 'success')
    
    return redirect(url_for('dosing.manage_profiles'))

@dosing_bp.route('/profiles/add', methods=['GET', 'POST'])
def add_profile():
    """Add a new plant profile"""
    if request.method == 'POST':
        # Get profile details from form
        name = request.form.get('name')
        description = request.form.get('description')
        ph_setpoint = request.form.get('ph_setpoint', type=float)
        ph_buffer = request.form.get('ph_buffer', type=float)
        ec_setpoint = request.form.get('ec_setpoint', type=float)
        ec_buffer = request.form.get('ec_buffer', type=float)
        temp_min = request.form.get('temp_min', type=float)
        temp_max = request.form.get('temp_max', type=float)
        
        # Get nutrient components
        component_pumps = request.form.getlist('component_pumps[]')
        component_ratios = request.form.getlist('component_ratios[]')
        
        # Validate input
        if not name:
            flash('Profile name is required', 'error')
            return redirect(url_for('dosing.add_profile'))
        
        if not component_pumps:
            flash('At least one nutrient component is required', 'error')
            return redirect(url_for('dosing.add_profile'))
        
        # Generate a unique profile ID
        profile_id = f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get existing profiles
        plant_profiles = Settings.get('plant_profiles', {})
        
        # Create nutrient components from form data
        nutrient_components = []
        for i in range(len(component_pumps)):
            if i < len(component_ratios):
                pump_id = int(component_pumps[i])
                ratio = float(component_ratios[i])
                pump = Pump.query.get(pump_id)
                
                if pump:
                    nutrient_components.append({
                        'pump_id': pump_id,
                        'pump_name': pump.name,
                        'ratio': ratio
                    })
        
        # Create the new profile
        plant_profiles[profile_id] = {
            'name': name,
            'description': description or f"Custom profile for {name}",
            'ph_setpoint': ph_setpoint or 6.0,
            'ph_buffer': ph_buffer or 0.2,
            'ec_setpoint': ec_setpoint or 1350,
            'ec_buffer': ec_buffer or 150,
            'temp_min': temp_min or 18.0,
            'temp_max': temp_max or 28.0,
            'nutrient_components': nutrient_components,
            'custom': True
        }
        
        # Save to database
        Settings.set('plant_profiles', plant_profiles)
        
        flash(f'Plant profile "{name}" added successfully', 'success')
        return redirect(url_for('dosing.manage_profiles'))
    
    # For GET requests, show the add profile form
    # Get all nutrient pumps for the components section
    nutrient_pumps = Pump.query.filter(
        Pump.type == 'nutrient',
        Pump.enabled == True
    ).all()
    
    return render_template('dosing/profile_form.html', profile=None, action='add', pumps=nutrient_pumps)

@dosing_bp.route('/profiles/edit/<profile_id>', methods=['GET', 'POST'])
def edit_profile(profile_id):
    """Edit an existing plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    # Get the profile
    profile = plant_profiles[profile_id]
    
    # Check if this is a default profile
    default_profiles = ['general', 'leafy_greens', 'fruiting', 'herbs', 'strawberries']
    if profile_id in default_profiles:
        flash('Default profiles cannot be edited', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    if request.method == 'POST':
        # Get profile details from form
        name = request.form.get('name')
        description = request.form.get('description')
        ph_setpoint = request.form.get('ph_setpoint', type=float)
        ph_buffer = request.form.get('ph_buffer', type=float)
        ec_setpoint = request.form.get('ec_setpoint', type=float)
        ec_buffer = request.form.get('ec_buffer', type=float)
        temp_min = request.form.get('temp_min', type=float)
        temp_max = request.form.get('temp_max', type=float)
        
        # Get nutrient components
        component_pumps = request.form.getlist('component_pumps[]')
        component_ratios = request.form.getlist('component_ratios[]')
        
        # Validate input
        if not name:
            flash('Profile name is required', 'error')
            return redirect(url_for('dosing.edit_profile', profile_id=profile_id))
        
        if not component_pumps:
            flash('At least one nutrient component is required', 'error')
            return redirect(url_for('dosing.edit_profile', profile_id=profile_id))
        
        # Create nutrient components from form data
        nutrient_components = []
        for i in range(len(component_pumps)):
            if i < len(component_ratios):
                pump_id = int(component_pumps[i])
                ratio = float(component_ratios[i])
                pump = Pump.query.get(pump_id)
                
                if pump:
                    nutrient_components.append({
                        'pump_id': pump_id,
                        'pump_name': pump.name,
                        'ratio': ratio
                    })
        
        # Update the profile
        profile['name'] = name
        profile['description'] = description or f"Custom profile for {name}"
        profile['ph_setpoint'] = ph_setpoint or 6.0
        profile['ph_buffer'] = ph_buffer or 0.2
        profile['ec_setpoint'] = ec_setpoint or 1350
        profile['ec_buffer'] = ec_buffer or 150
        profile['temp_min'] = temp_min or 18.0
        profile['temp_max'] = temp_max or 28.0
        profile['nutrient_components'] = nutrient_components
        
        # Save to database
        plant_profiles[profile_id] = profile
        Settings.set('plant_profiles', plant_profiles)
        
        flash(f'Plant profile "{name}" updated successfully', 'success')
        return redirect(url_for('dosing.manage_profiles'))
    
    # For GET requests, show the edit profile form
    # Get all nutrient pumps for the components section
    nutrient_pumps = Pump.query.filter(
        Pump.type == 'nutrient',
        Pump.enabled == True
    ).all()
    
    return render_template(
        'dosing/profile_form.html',
        profile=profile,
        profile_id=profile_id,
        action='edit',
        pumps=nutrient_pumps
    )

@dosing_bp.route('/profiles/delete/<profile_id>', methods=['POST'])
def delete_profile(profile_id):
    """Delete a plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    # Check if this is a default profile
    default_profiles = ['general', 'leafy_greens', 'fruiting', 'herbs', 'strawberries']
    if profile_id in default_profiles:
        flash('Default profiles cannot be deleted', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    # Check if this is the active profile
    active_profile = Settings.get('active_plant_profile', 'general')
    if profile_id == active_profile:
        # Set active profile to general
        Settings.set('active_plant_profile', 'general')
        flash('Active profile switched to General Purpose', 'warning')
    
    # Get the profile name for the message
    profile_name = plant_profiles[profile_id]['name']
    
    # Delete the profile
    del plant_profiles[profile_id]
    Settings.set('plant_profiles', plant_profiles)
    
    flash(f'Plant profile "{profile_name}" deleted successfully', 'success')
    return redirect(url_for('dosing.manage_profiles'))

@dosing_bp.route('/profiles/duplicate/<profile_id>', methods=['POST'])
def duplicate_profile(profile_id):
    """Duplicate a plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    # Get the source profile
    source_profile = plant_profiles[profile_id]
    
    # Create a copy
    new_profile = copy.deepcopy(source_profile)
    new_profile['name'] = f"Copy of {new_profile['name']}"
    
    # Generate a unique profile ID
    new_profile_id = f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Add custom flag
    new_profile['custom'] = True
    
    # Add to profiles
    plant_profiles[new_profile_id] = new_profile
    Settings.set('plant_profiles', plant_profiles)
    
    flash(f'Plant profile "{new_profile["name"]}" created successfully', 'success')
    return redirect(url_for('dosing.manage_profiles'))

@dosing_bp.route('/grow-cycle', methods=['GET', 'POST'])
def grow_cycle():
    """Manage cannabis grow cycle"""
    # Get the cannabis profile
    plant_profiles = Settings.get('plant_profiles', {})
    cannabis_profile = plant_profiles.get('cannabis', {})
    
    if not cannabis_profile:
        flash('Cannabis profile not found', 'error')
        return redirect(url_for('dosing.manage_profiles'))
    
    if request.method == 'POST':
        # Handle week advancement
        action = request.form.get('action')
        
        if action == 'set_week':
            new_week = request.form.get('week', type=int)
            if new_week and 1 <= new_week <= cannabis_profile.get('total_weeks', 12):
                old_week = cannabis_profile.get('current_week', 1)
                # Update the week
                cannabis_profile['current_week'] = new_week
                plant_profiles['cannabis'] = cannabis_profile
                Settings.set('plant_profiles', plant_profiles)
                
                # Run auto-configuration to update nutrient components
                update_result = Settings.auto_configure_nutrient_components()
                
                flash(f'Grow cycle week updated from Week {old_week} to Week {new_week}. {update_result}', 'success')
                return redirect(url_for('dosing.grow_cycle'))
            else:
                flash(f'Invalid week value: {new_week}. Week must be between 1 and {cannabis_profile.get("total_weeks", 12)}', 'error')
                return redirect(url_for('dosing.grow_cycle'))
        
        elif action == 'next_week':
            current_week = cannabis_profile.get('current_week', 1)
            total_weeks = cannabis_profile.get('total_weeks', 12)
            
            if current_week < total_weeks:
                # Update to the next week
                cannabis_profile['current_week'] = current_week + 1
                plant_profiles['cannabis'] = cannabis_profile
                Settings.set('plant_profiles', plant_profiles)
                
                # Run auto-configuration to update nutrient components
                update_result = Settings.auto_configure_nutrient_components()
                
                flash(f'Grow cycle advanced to Week {current_week + 1}. {update_result}', 'success')
            else:
                flash('Already at the final week of the grow cycle', 'warning')
            
            return redirect(url_for('dosing.grow_cycle'))
        
        elif action == 'reset_cycle':
            old_week = cannabis_profile.get('current_week', 1)
            cannabis_profile['current_week'] = 1
            plant_profiles['cannabis'] = cannabis_profile
            Settings.set('plant_profiles', plant_profiles)
            
            # Run auto-configuration to update nutrient components
            update_result = Settings.auto_configure_nutrient_components()
            
            flash(f'Grow cycle reset from Week {old_week} to Week 1. {update_result}', 'success')
            return redirect(url_for('dosing.grow_cycle'))
        
        else:
            flash(f'Unknown action: {action}', 'error')
            return redirect(url_for('dosing.grow_cycle'))
    
    # Get current week and weekly schedules
    current_week = cannabis_profile.get('current_week', 1)
    total_weeks = cannabis_profile.get('total_weeks', 12)
    weekly_schedules = cannabis_profile.get('weekly_schedules', {})
    
    # Get current week schedule
    current_week_str = str(current_week)
    current_schedule = weekly_schedules.get(current_week_str, {})
    
    # Get growth phase label
    growth_phase = "Unknown"
    if 1 <= current_week <= 2:
        growth_phase = "Seedling"
    elif 3 <= current_week <= 5:
        growth_phase = "Vegetative"
    elif current_week == 6:
        growth_phase = "Pre-Flower"
    elif 7 <= current_week <= 11:
        growth_phase = "Flowering"
    elif current_week == 12:
        growth_phase = "Flush"
    
    # Check nutrient components to ensure they match the current week
    nutrient_components = cannabis_profile.get('nutrient_components', [])
    all_components_match = all(comp.get('weekly_schedule_applied') == current_week_str for comp in nutrient_components)
    
    if not all_components_match and nutrient_components:
        # Force an update to ensure components match the current week
        update_result = Settings.auto_configure_nutrient_components()
        flash(f'Updated nutrient components to match current week: {update_result}', 'info')
    
    return render_template(
        'dosing/grow_cycle.html',
        profile=cannabis_profile,
        current_week=current_week,
        total_weeks=total_weeks,
        weekly_schedules=weekly_schedules,
        current_schedule=current_schedule,
        growth_phase=growth_phase
    )

@dosing_bp.route('/profile_form')
def profile_form():
    # This route is mentioned in the code but not implemented in the provided file
    # It's left unchanged as it's mentioned in the code
    pass

@dosing_bp.route('/nutrients', methods=['GET'])
def nutrients():
    """Display and manage nutrient database"""
    # Get all nutrient brands and products
    brands = NutrientBrand.query.all()
    
    # Organize products by brand
    organized_brands = []
    for brand in brands:
        brand_data = brand.to_dict()
        # Sort products alphabetically
        brand_data['products'].sort(key=lambda x: x['name'])
        organized_brands.append(brand_data)
    
    # Sort brands alphabetically, but keep Custom brand at the end
    organized_brands.sort(key=lambda x: (x['name'] == 'Custom', x['name']))
    
    return render_template(
        'dosing/nutrients.html',
        brands=organized_brands,
        nutrient_types=[
            {'id': 'grow', 'name': 'Grow'},
            {'id': 'bloom', 'name': 'Bloom'},
            {'id': 'micro', 'name': 'Micro'},
            {'id': 'calmag', 'name': 'CalMag'},
            {'id': 'other', 'name': 'Other'}
        ]
    ) 