from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.settings import Settings
from app.models.pump import Pump
from app import db
from app.models.nutrient import NutrientBrand, NutrientProduct
import uuid
from datetime import datetime
import copy

# Create a blueprint
garden_bp = Blueprint('garden', __name__)

@garden_bp.route('/')
def index():
    """Garden dashboard page"""
    # Get the active profile
    active_profile_id = Settings.get('active_plant_profile', 'general')
    plant_profiles = Settings.get('plant_profiles', {})
    active_profile = plant_profiles.get(active_profile_id, {})
    
    return render_template(
        'garden/index.html',
        active_profile=active_profile,
        active_profile_id=active_profile_id
    )

@garden_bp.route('/profiles')
def profiles():
    """Plant profiles management"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Get the active profile
    active_profile = Settings.get('active_plant_profile', 'general')
    
    # Pass all profiles to template
    return render_template(
        'garden/profiles.html',
        plant_profiles=plant_profiles,
        active_profile=active_profile,
        is_admin=True  # You might want to change this based on user authentication
    )

@garden_bp.route('/profiles/reconfigure', methods=['POST'])
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
    
    return redirect(url_for('garden.profiles'))

@garden_bp.route('/profiles/add', methods=['GET', 'POST'])
def add_profile():
    """Add a new plant profile"""
    # Get existing profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Get all available pumps for components
    pumps = Pump.query.filter(
        Pump.type.in_(['nutrient', 'ph_up', 'ph_down']),
        Pump.enabled == True
    ).all()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        ph_setpoint = request.form.get('ph_setpoint', type=float)
        ph_buffer = request.form.get('ph_buffer', type=float)
        ec_setpoint = request.form.get('ec_setpoint', type=int)
        ec_buffer = request.form.get('ec_buffer', type=int)
        temp_min = request.form.get('temp_min', type=float)
        temp_max = request.form.get('temp_max', type=float)
        
        # Check if weekly schedule should be used
        use_weekly_schedule = 'use_weekly_schedule' in request.form
        total_weeks = request.form.get('total_weeks', type=int) if use_weekly_schedule else None
        growth_phases_text = request.form.get('growth_phases') if use_weekly_schedule else None
        
        # Process nutrient components
        component_pumps = request.form.getlist('component_pumps[]')
        component_ratios = request.form.getlist('component_ratios[]')
        
        # Validate form data
        if not name:
            flash('Profile name is required.', 'error')
            return redirect(url_for('garden.add_profile'))
        
        # Create a profile ID from the name
        profile_id = name.lower().replace(' ', '_')
        
        # Check if profile already exists
        if profile_id in plant_profiles:
            flash(f'A profile with the name "{name}" already exists.', 'error')
            return redirect(url_for('garden.add_profile'))
        
        # Create base profile
        new_profile = {
            'name': name,
            'description': description,
            'ph_setpoint': ph_setpoint or 6.0,
            'ph_buffer': ph_buffer or 0.2,
            'ec_setpoint': ec_setpoint or 1350,
            'ec_buffer': ec_buffer or 150,
            'temp_min': temp_min or 18.0,
            'temp_max': temp_max or 28.0,
            'custom': True,
            'nutrient_ratios': {
                'grow': 1.0,
                'bloom': 1.0,
                'micro': 1.0,
                'calmag': 0.5
            },
            'nutrient_components': []
        }
        
        # Set up weekly schedule if requested
        if use_weekly_schedule and total_weeks:
            new_profile['weekly_schedules'] = {}
            new_profile['total_weeks'] = total_weeks
            new_profile['current_week'] = 1
            
            # Create default weekly schedules
            for week in range(1, total_weeks + 1):
                new_profile['weekly_schedules'][str(week)] = {
                    'ec_setpoint': ec_setpoint,
                    'nutrient_ratios': new_profile['nutrient_ratios'].copy()
                }
            
            # Store growth phases if provided
            if growth_phases_text:
                new_profile['growth_phases'] = growth_phases_text
        
        # Process nutrient components
        components = []
        for i in range(min(len(component_pumps), len(component_ratios))):
            pump_id = component_pumps[i]
            ratio = float(component_ratios[i])
            
            # Find the pump
            pump = next((p for p in pumps if str(p.id) == pump_id), None)
            if pump:
                # Add component
                component = {
                    'pump_id': pump.id,
                    'pump_name': pump.name,
                    'nutrient_name': pump.nutrient_name,
                    'ratio': ratio,
                    'type': pump.type
                }
                components.append(component)
        
        new_profile['nutrient_components'] = components
        
        # Save the new profile
        plant_profiles[profile_id] = new_profile
        Settings.set('plant_profiles', plant_profiles)
        
        # Run auto-configuration to update nutrient components
        update_result = Settings.auto_configure_nutrient_components()
        
        flash(f'Plant profile "{name}" added successfully. {update_result}', 'success')
        return redirect(url_for('garden.profiles'))
    
    # For GET requests, show the add profile form
    # Create empty profile for the template
    empty_profile = {
        'name': '',
        'description': '',
        'ph_setpoint': 6.0,
        'ph_buffer': 0.2,
        'ec_setpoint': 1350,
        'ec_buffer': 150,
        'temp_min': 18.0,
        'temp_max': 28.0,
        'nutrient_components': [],
        'nutrient_ratios': {
            'grow': 1.0,
            'bloom': 1.0,
            'micro': 1.0,
            'calmag': 0.5
        }
    }
    
    # Set defaults for weekly schedule variables
    current_week = 1
    total_weeks = 12
    weekly_schedules = {}
    current_schedule = None
    growth_phase = "Seedling"  # Default for new profiles
    
    # Create default growth phases
    growth_phases = {}
    for week in range(1, total_weeks + 1):
        if week <= 3:
            growth_phases[week] = "Seedling"
        elif week <= 6:
            growth_phases[week] = "Vegetative"
        else:
            growth_phases[week] = "Flowering"
    
    # Get general settings to pass to template
    settings = {
        'dark_mode': Settings.get('dark_mode', True)
    }
    
    return render_template(
        'garden/profile_form.html',
        profile=empty_profile,
        action='add',
        pumps=pumps,
        current_week=current_week,
        total_weeks=total_weeks,
        weekly_schedules=weekly_schedules,
        current_schedule=current_schedule,
        growth_phase=growth_phase,
        growth_phases=growth_phases,
        settings=settings
    )

@garden_bp.route('/profiles/edit/<profile_id>', methods=['GET', 'POST'])
def edit_profile(profile_id):
    """Edit an existing plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found.', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Get the profile
    profile = plant_profiles[profile_id]
    
    # Get all available pumps for components
    pumps = Pump.query.filter(
        Pump.type.in_(['nutrient', 'ph_up', 'ph_down']),
        Pump.enabled == True
    ).all()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        ph_setpoint = request.form.get('ph_setpoint', type=float)
        ph_buffer = request.form.get('ph_buffer', type=float)
        ec_setpoint = request.form.get('ec_setpoint', type=int)
        ec_buffer = request.form.get('ec_buffer', type=int)
        temp_min = request.form.get('temp_min', type=float)
        temp_max = request.form.get('temp_max', type=float)
        
        # Check if weekly schedule should be used
        use_weekly_schedule = 'use_weekly_schedule' in request.form
        total_weeks = request.form.get('total_weeks', type=int) if use_weekly_schedule else None
        growth_phases_text = request.form.get('growth_phases') if use_weekly_schedule else None
        
        # Process nutrient components
        component_pumps = request.form.getlist('component_pumps[]')
        component_ratios = request.form.getlist('component_ratios[]')
        
        # Validate form data
        if not name:
            flash('Profile name is required.', 'error')
            return redirect(url_for('garden.edit_profile', profile_id=profile_id))
        
        # Update the profile
        profile['name'] = name
        profile['description'] = description
        profile['ph_setpoint'] = ph_setpoint or 6.0
        profile['ph_buffer'] = ph_buffer or 0.2
        profile['ec_setpoint'] = ec_setpoint or 1350
        profile['ec_buffer'] = ec_buffer or 150
        profile['temp_min'] = temp_min or 18.0
        profile['temp_max'] = temp_max or 28.0
        
        # Handle weekly schedules
        if use_weekly_schedule and total_weeks:
            # Check if we're adding weekly schedules for the first time
            if 'weekly_schedules' not in profile:
                profile['weekly_schedules'] = {}
                profile['current_week'] = 1
            
            # Update total weeks
            profile['total_weeks'] = total_weeks
            
            # Make sure we have entries for each week
            for week in range(1, total_weeks + 1):
                week_str = str(week)
                if week_str not in profile.get('weekly_schedules', {}):
                    profile.setdefault('weekly_schedules', {})[week_str] = {
                        'ec_setpoint': ec_setpoint,
                        'nutrient_ratios': profile.get('nutrient_ratios', {}).copy()
                    }
            
            # Store growth phases if provided
            if growth_phases_text:
                profile['growth_phases'] = growth_phases_text
        else:
            # Remove weekly schedules if they existed
            if 'weekly_schedules' in profile:
                del profile['weekly_schedules']
            if 'total_weeks' in profile:
                del profile['total_weeks']
            if 'current_week' in profile:
                del profile['current_week']
            if 'growth_phases' in profile:
                del profile['growth_phases']
        
        # Update nutrient components
        components = []
        for i in range(min(len(component_pumps), len(component_ratios))):
            pump_id = component_pumps[i]
            ratio = float(component_ratios[i])
            
            # Find the pump
            pump = next((p for p in pumps if str(p.id) == pump_id), None)
            if pump:
                # Add component
                component = {
                    'pump_id': pump.id,
                    'pump_name': pump.name,
                    'nutrient_name': pump.nutrient_name,
                    'ratio': ratio,
                    'type': pump.type
                }
                components.append(component)
        
        profile['nutrient_components'] = components
        
        # Save the updated profile
        plant_profiles[profile_id] = profile
        Settings.set('plant_profiles', plant_profiles)
        
        # Run auto-configuration to update nutrient components
        update_result = Settings.auto_configure_nutrient_components()
        
        flash(f'Plant profile "{name}" updated successfully. {update_result}', 'success')
        return redirect(url_for('garden.profiles'))
    
    # For GET requests, show the edit profile form
    # Make a deep copy of the profile to avoid modifying the original
    profile_copy = copy.deepcopy(profile)
    
    # Get weekly schedule info if this profile uses weekly schedules
    current_week = profile_copy.get('current_week', 1)
    total_weeks = profile_copy.get('total_weeks', 12)
    weekly_schedules = profile_copy.get('weekly_schedules', {})
    
    # Get current week schedule and growth phase if available
    current_schedule = None
    growth_phase = None
    if weekly_schedules:
        current_week_str = str(current_week)
        current_schedule = weekly_schedules.get(current_week_str, {})
        growth_phase = get_growth_phase_for_week(profile_copy, current_week)
        
        # Get growth phase labels for each week
        growth_phases = {}
        for week in range(1, total_weeks + 1):
            growth_phases[week] = get_growth_phase_for_week(profile_copy, week)
    else:
        growth_phases = {}
    
    # Get general settings to pass to template
    settings = {
        'dark_mode': Settings.get('dark_mode', True)
    }
    
    return render_template(
        'garden/profile_form.html',
        profile=profile_copy,
        profile_id=profile_id,
        action='edit',
        pumps=pumps,
        current_week=current_week,
        total_weeks=total_weeks,
        weekly_schedules=weekly_schedules,
        current_schedule=current_schedule,
        growth_phase=growth_phase,
        growth_phases=growth_phases,
        settings=settings
    )

@garden_bp.route('/profiles/delete/<profile_id>', methods=['POST'])
def delete_profile(profile_id):
    """Delete a plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found.', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Check if this is the active profile
    active_profile = Settings.get('active_plant_profile', 'general')
    if profile_id == active_profile:
        flash('Cannot delete the active profile. Please activate another profile first.', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Get the profile name for the message
    profile_name = plant_profiles[profile_id].get('name', profile_id)
    
    # Check if this is one of the default profiles
    if not plant_profiles[profile_id].get('custom', False):
        flash(f'Cannot delete the default profile "{profile_name}".', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Delete the profile
    del plant_profiles[profile_id]
    Settings.set('plant_profiles', plant_profiles)
    
    flash(f'Profile "{profile_name}" deleted successfully.', 'success')
    return redirect(url_for('garden.profiles'))

@garden_bp.route('/profiles/duplicate/<profile_id>', methods=['POST'])
def duplicate_profile(profile_id):
    """Duplicate a plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found.', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Get the profile to duplicate
    source_profile = plant_profiles[profile_id]
    
    # Generate a new ID
    new_id = profile_id + '_copy_' + uuid.uuid4().hex[:6]
    
    # Create a deep copy of the profile
    new_profile = copy.deepcopy(source_profile)
    
    # Update the name
    new_profile['name'] = new_profile.get('name', profile_id) + ' (Copy)'
    
    # Mark as custom
    new_profile['custom'] = True
    
    # Save the new profile
    plant_profiles[new_id] = new_profile
    Settings.set('plant_profiles', plant_profiles)
    
    flash(f'Profile duplicated successfully as "{new_profile["name"]}".', 'success')
    return redirect(url_for('garden.profiles'))

@garden_bp.route('/profiles/activate/<profile_id>', methods=['POST'])
def activate_profile(profile_id):
    """Set a profile as the active plant profile"""
    # Get all plant profiles
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found.', 'error')
        return redirect(url_for('garden.profiles'))
    
    # Get the profile
    profile = plant_profiles[profile_id]
    profile_name = profile.get('name', profile_id)
    
    # Set as active profile
    Settings.set('active_plant_profile', profile_id)
    
    # Update system settings to match profile settings
    Settings.set('ph_setpoint', profile.get('ph_setpoint', 6.0))
    Settings.set('ph_buffer', profile.get('ph_buffer', 0.2))
    Settings.set('ec_setpoint', profile.get('ec_setpoint', 1350))
    Settings.set('ec_buffer', profile.get('ec_buffer', 150))
    
    # If it's a weekly schedule profile like cannabis, use the current week's settings
    if 'weekly_schedules' in profile and profile.get('current_week'):
        current_week = str(profile.get('current_week'))
        weekly_schedule = profile.get('weekly_schedules', {}).get(current_week, {})
        
        # If the weekly schedule has EC setpoint, use that
        if 'ec_setpoint' in weekly_schedule:
            Settings.set('ec_setpoint', weekly_schedule.get('ec_setpoint'))
    
    # Run auto-configuration to update nutrient components
    update_result = Settings.auto_configure_nutrient_components()
    
    flash(f'"{profile_name}" is now the active plant profile. Dosing settings have been updated to match. {update_result}', 'success')
    return redirect(url_for('garden.profiles'))

@garden_bp.route('/profiles/schedule/<profile_id>')
def profile_schedule(profile_id):
    """Weekly schedule management for a specific profile"""
    # Get the profile data
    plant_profiles = Settings.get('plant_profiles', {})
    
    # Check if profile exists
    if profile_id not in plant_profiles:
        flash('Profile not found.', 'error')
        return redirect(url_for('garden.profiles'))
    
    profile = plant_profiles[profile_id]
    
    # Check if profile has weekly schedules
    if not profile.get('weekly_schedules'):
        flash('This profile does not use weekly schedules.', 'info')
        return redirect(url_for('garden.edit_profile', profile_id=profile_id))
    
    weekly_schedules = profile.get('weekly_schedules', {})
    current_week = profile.get('current_week', 1)
    total_weeks = profile.get('total_weeks', 12)
    
    # Make sure we have entries for each week up to total_weeks
    for week in range(1, total_weeks + 1):
        week_str = str(week)
        if week_str not in weekly_schedules:
            # Create a default schedule for this week
            weekly_schedules[week_str] = {
                'ec_setpoint': profile.get('ec_setpoint', 1200),
                'nutrient_ratios': profile.get('nutrient_ratios', {
                    'grow': 1.0,
                    'bloom': 1.0,
                    'micro': 1.0,
                    'calmag': 1.0
                })
            }
    
    # Sort the weeks for display
    sorted_weeks = sorted([str(i) for i in range(1, total_weeks + 1)], key=int)
    
    # Get growth phase labels for each week (define this function if it doesn't exist)
    growth_phases = {}
    for week in range(1, total_weeks + 1):
        growth_phases[week] = get_growth_phase_for_week(profile, week)
    
    # Get general settings to pass to template
    settings = {
        'dark_mode': Settings.get('dark_mode', True)
    }
    
    return render_template(
        'garden/profile_schedule.html',
        profile=profile,
        profile_id=profile_id,
        current_week=current_week,
        total_weeks=total_weeks,
        weekly_schedules=weekly_schedules,
        sorted_weeks=sorted_weeks,
        growth_phases=growth_phases,
        settings=settings
    )

@garden_bp.route('/nutrients', methods=['GET'])
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
        'garden/nutrients.html',
        brands=organized_brands,
        nutrient_types=[
            {'id': 'grow', 'name': 'Grow'},
            {'id': 'bloom', 'name': 'Bloom'},
            {'id': 'micro', 'name': 'Micro'},
            {'id': 'calmag', 'name': 'CalMag'},
            {'id': 'other', 'name': 'Other'}
        ]
    )

@garden_bp.route('/grow-cycle', methods=['GET', 'POST'])
def grow_cycle():
    """Manage plant grow cycle for any plant profile with weekly schedules"""
    # Get the active plant profile
    plant_profiles = Settings.get('plant_profiles', {})
    active_profile_id = Settings.get('active_plant_profile', 'general')
    active_profile = plant_profiles.get(active_profile_id, {})
    
    # Check if the active profile has weekly schedules
    if not active_profile or 'weekly_schedules' not in active_profile:
        # Try to find any profile with weekly schedules as a fallback
        for profile_id, profile in plant_profiles.items():
            if 'weekly_schedules' in profile:
                if not active_profile:
                    active_profile = profile
                    active_profile_id = profile_id
                    break
                    
    # If no profile with weekly schedules is found, show a message
    if not active_profile or 'weekly_schedules' not in active_profile:
        flash('No active profile with a grow cycle schedule was found. Please activate a profile that uses weekly scheduling.', 'warning')
        
        # Get general settings to pass to template
        settings = {
            'dark_mode': Settings.get('dark_mode', True)
        }
        
        return render_template(
            'garden/grow_cycle.html',
            no_schedule=True,
            settings=settings
        )
    
    if request.method == 'POST':
        # Handle week advancement
        action = request.form.get('action')
        
        if action == 'set_week':
            new_week = request.form.get('week', type=int)
            if new_week and 1 <= new_week <= active_profile.get('total_weeks', 12):
                old_week = active_profile.get('current_week', 1)
                # Update the week
                active_profile['current_week'] = new_week
                plant_profiles[active_profile_id] = active_profile
                Settings.set('plant_profiles', plant_profiles)
                
                # Update system settings if this is the active profile
                if Settings.get('active_plant_profile') == active_profile_id:
                    weekly_schedule = active_profile.get('weekly_schedules', {}).get(str(new_week), {})
                    if 'ec_setpoint' in weekly_schedule:
                        Settings.set('ec_setpoint', weekly_schedule.get('ec_setpoint'))
                
                # Run auto-configuration to update nutrient components
                update_result = Settings.auto_configure_nutrient_components()
                
                flash(f'Grow cycle week updated from Week {old_week} to Week {new_week}. Dosing settings have been updated. {update_result}', 'success')
                return redirect(url_for('garden.grow_cycle'))
            else:
                flash(f'Invalid week value: {new_week}. Week must be between 1 and {active_profile.get("total_weeks", 12)}', 'error')
                return redirect(url_for('garden.grow_cycle'))
        
        elif action == 'next_week':
            current_week = active_profile.get('current_week', 1)
            total_weeks = active_profile.get('total_weeks', 12)
            
            if current_week < total_weeks:
                # Update to the next week
                active_profile['current_week'] = current_week + 1
                plant_profiles[active_profile_id] = active_profile
                Settings.set('plant_profiles', plant_profiles)
                
                # Update system settings if this is the active profile
                if Settings.get('active_plant_profile') == active_profile_id:
                    weekly_schedule = active_profile.get('weekly_schedules', {}).get(str(current_week + 1), {})
                    if 'ec_setpoint' in weekly_schedule:
                        Settings.set('ec_setpoint', weekly_schedule.get('ec_setpoint'))
                
                # Run auto-configuration to update nutrient components
                update_result = Settings.auto_configure_nutrient_components()
                
                flash(f'Grow cycle advanced to Week {current_week + 1}. Dosing settings have been updated. {update_result}', 'success')
            else:
                flash('Already at the final week of the grow cycle', 'warning')
            
            return redirect(url_for('garden.grow_cycle'))
        
        elif action == 'reset_cycle':
            old_week = active_profile.get('current_week', 1)
            active_profile['current_week'] = 1
            plant_profiles[active_profile_id] = active_profile
            Settings.set('plant_profiles', plant_profiles)
            
            # Update system settings if this is the active profile
            if Settings.get('active_plant_profile') == active_profile_id:
                weekly_schedule = active_profile.get('weekly_schedules', {}).get('1', {})
                if 'ec_setpoint' in weekly_schedule:
                    Settings.set('ec_setpoint', weekly_schedule.get('ec_setpoint'))
            
            # Run auto-configuration to update nutrient components
            update_result = Settings.auto_configure_nutrient_components()
            
            flash(f'Grow cycle reset from Week {old_week} to Week 1. Dosing settings have been updated. {update_result}', 'success')
            return redirect(url_for('garden.grow_cycle'))
        
        else:
            flash(f'Unknown action: {action}', 'error')
            return redirect(url_for('garden.grow_cycle'))
    
    # Get current week and weekly schedules
    current_week = active_profile.get('current_week', 1)
    total_weeks = active_profile.get('total_weeks', 12)
    weekly_schedules = active_profile.get('weekly_schedules', {})
    
    # Get current week schedule
    current_week_str = str(current_week)
    current_schedule = weekly_schedules.get(current_week_str, {})
    
    # Get growth phase label
    growth_phase = get_growth_phase_for_week(active_profile, current_week)
    
    # Check nutrient components to ensure they match the current week
    nutrient_components = active_profile.get('nutrient_components', [])
    all_components_match = all(comp.get('weekly_schedule_applied') == current_week_str for comp in nutrient_components)
    
    if not all_components_match and nutrient_components:
        # Force an update to ensure components match the current week
        update_result = Settings.auto_configure_nutrient_components()
        flash(f'Updated nutrient components to match current week: {update_result}', 'info')
    
    # Get growth phase labels for each week
    growth_phases = {}
    for week in range(1, total_weeks + 1):
        growth_phases[week] = get_growth_phase_for_week(active_profile, week)
    
    # Get general settings to pass to template
    settings = {
        'dark_mode': Settings.get('dark_mode', True)
    }
    
    return render_template(
        'garden/grow_cycle.html',
        profile=active_profile,
        profile_id=active_profile_id,
        current_week=current_week,
        total_weeks=total_weeks,
        weekly_schedules=weekly_schedules,
        current_schedule=current_schedule,
        growth_phase=growth_phase,
        growth_phases=growth_phases,
        no_schedule=False,
        settings=settings
    )

# Helper function for profile schedules
def get_growth_phase_for_week(profile, week):
    """Get the growth phase label for a specific week"""
    growth_phases_text = profile.get('growth_phases', '')
    
    if not growth_phases_text:
        # Default phases if not defined
        if week <= 3:
            return "Seedling"
        elif week <= 6:
            return "Vegetative"
        else:
            return "Flowering"
    
    # Parse the growth phases text
    # Expected format: "Seedling: 1-3, Vegetative: 4-6, Flowering: 7-12"
    # Or "1-3: Seedling\n4-6: Vegetative\n7-12: Flowering"
    phases = {}
    try:
        # First, normalize the string - replace newlines with commas
        normalized_text = growth_phases_text.replace('\r\n', ',').replace('\n', ',')
        
        for phase_entry in normalized_text.split(','):
            phase_entry = phase_entry.strip()
            if not phase_entry or ':' not in phase_entry:
                continue
                
            # Split by colon
            parts = [p.strip() for p in phase_entry.split(':', 1)]
            
            # Determine which part is the phase name and which is the week range
            if parts[0].replace('-', '').replace(' ', '').isdigit() or parts[0].isdigit():
                # Format is "1-3: Seedling" or "1: Seedling"
                weeks_range, phase_name = parts
            else:
                # Format is "Seedling: 1-3" or "Seedling: 1"
                phase_name, weeks_range = parts
            
            # Process week ranges
            for week_range in weeks_range.split(','):
                week_range = week_range.strip()
                if '-' in week_range:
                    try:
                        start, end = map(int, week_range.split('-'))
                        for w in range(start, end + 1):
                            phases[w] = phase_name
                    except ValueError:
                        # Skip invalid ranges
                        continue
                else:
                    try:
                        w = int(week_range)
                        phases[w] = phase_name
                    except ValueError:
                        # Skip invalid week numbers
                        continue
    except Exception as e:
        # If any parsing error occurs, fall back to defaults
        if week <= 3:
            return "Seedling"
        elif week <= 6:
            return "Vegetative"
        else:
            return "Flowering"
    
    return phases.get(week, "Unknown") 