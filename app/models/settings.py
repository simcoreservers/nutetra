from app import db
import json
from app.models.pump import Pump

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f'<Settings {self.key}: {self.value}>'
    
    @staticmethod
    def get(key, default=None):
        """Get a setting value by key"""
        setting = Settings.query.filter_by(key=key).first()
        if setting is None:
            return default
        
        # Try to parse JSON, if it fails return the raw value
        try:
            return json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            return setting.value
    
    @staticmethod
    def set(key, value):
        """Set a setting value"""
        # Convert non-string values to JSON
        if not isinstance(value, str):
            value = json.dumps(value)
            
        setting = Settings.query.filter_by(key=key).first()
        if setting is None:
            setting = Settings(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
            
        db.session.commit()
        return setting
    
    @staticmethod
    def get_all():
        """Get all settings as a dictionary"""
        settings = {}
        for setting in Settings.query.all():
            try:
                settings[setting.key] = json.loads(setting.value)
            except (json.JSONDecodeError, TypeError):
                settings[setting.key] = setting.value
        return settings
    
    @classmethod
    def initialize_defaults(cls, force_reset=False):
        """Initialize default settings
        
        Args:
            force_reset: If True, this will reset existing plant profiles to their defaults
        """
        # Get existing profiles
        existing_profiles = None
        if force_reset:
            existing_profiles = cls.get('plant_profiles')
        
        # Initialize plant profiles without nutrient components
        # Components will be auto-configured based on available pumps
        plant_profiles = {
            'general': {
                'name': 'General',
                'description': 'General purpose profile for most plants',
                'ph_setpoint': 6.0,
                'ph_buffer': 0.2,
                'ec_setpoint': 1350,
                'ec_buffer': 150,
                'temp_min': 18.0,
                'temp_max': 28.0,
                'nutrient_components': [],
                'custom': False,
                'nutrient_ratios': {
                    'grow': 1.0,  # Balanced grow nutrients
                    'bloom': 1.0,  # Balanced bloom nutrients
                    'micro': 1.0,  # Balanced micro nutrients
                    'calmag': 0.5  # Lower ratio for calcium/magnesium
                }
            },
            'leafy_greens': {
                'name': 'Leafy Greens',
                'description': 'Optimal settings for lettuce, spinach, kale, etc.',
                'ph_setpoint': 6.0,
                'ph_buffer': 0.2,
                'ec_setpoint': 1200,
                'ec_buffer': 150,
                'temp_min': 15.0,
                'temp_max': 24.0,
                'nutrient_components': [],
                'custom': False,
                'nutrient_ratios': {
                    'grow': 1.5,   # Higher nitrogen for leafy growth
                    'bloom': 0.5,  # Lower P-K for leafy greens
                    'micro': 1.0,  # Normal micro nutrients
                    'calmag': 0.7  # Medium calcium/magnesium
                }
            },
            'fruiting': {
                'name': 'Fruiting',
                'description': 'For tomatoes, peppers, cucumbers and other fruiting plants',
                'ph_setpoint': 6.0,
                'ph_buffer': 0.2,
                'ec_setpoint': 1800,
                'ec_buffer': 150,
                'temp_min': 20.0,
                'temp_max': 28.0,
                'nutrient_components': [],
                'custom': False,
                'nutrient_ratios': {
                    'grow': 0.7,   # Lower nitrogen for fruiting stage
                    'bloom': 2.0,  # Higher P-K for fruit production
                    'micro': 1.0,  # Normal micro nutrients
                    'calmag': 1.0  # Higher calcium for fruit development
                }
            },
            'herbs': {
                'name': 'Herbs',
                'description': 'Ideal for basil, cilantro, parsley and other herbs',
                'ph_setpoint': 5.8,
                'ph_buffer': 0.2,
                'ec_setpoint': 1200,
                'ec_buffer': 100,
                'temp_min': 18.0,
                'temp_max': 26.0,
                'nutrient_components': [],
                'custom': False,
                'nutrient_ratios': {
                    'grow': 1.2,   # Higher nitrogen for leafy growth
                    'bloom': 0.7,  # Lower P-K for herbs
                    'micro': 1.0,  # Normal micro nutrients
                    'calmag': 0.5  # Lower calcium/magnesium
                }
            },
            'strawberries': {
                'name': 'Strawberries',
                'description': 'Optimized for growing strawberries',
                'ph_setpoint': 5.8,
                'ph_buffer': 0.2,
                'ec_setpoint': 1300,
                'ec_buffer': 100,
                'temp_min': 18.0,
                'temp_max': 26.0,
                'nutrient_components': [],
                'custom': False,
                'nutrient_ratios': {
                    'grow': 0.8,   # Moderate nitrogen for growth
                    'bloom': 1.8,  # Higher P-K for fruit production
                    'micro': 1.0,  # Normal micro nutrients
                    'calmag': 1.2  # Higher calcium for fruit quality
                }
            }
        }

        # Add settings if they don't exist
        if not cls.get('plant_profiles'):
            cls.set('plant_profiles', plant_profiles)
        
        # Make sure active_plant_profile exists and is valid
        active_profile = cls.get('active_plant_profile')
        if not active_profile or active_profile not in plant_profiles:
            cls.set('active_plant_profile', 'general')
        
        # Default settings - only set if they don't exist
        defaults = {
            'active_plant_profile': 'general',
            'plant_profiles': plant_profiles,
            'ec_setpoint': 1350,
            'ec_buffer': 150,
            'ph_setpoint': 6.0,
            'ph_buffer': 0.2,
            'temp_min': 18.0,
            'temp_max': 28.0,
            'cycle_interval': 300,
            'ph_calibration_offset': 0.0
        }
        
        # Set each default setting if it doesn't exist
        for key, value in defaults.items():
            if force_reset and key == 'plant_profiles':
                # If forcing a reset, always update plant profiles
                # But preserve custom profiles if they exist
                if existing_profiles:
                    # Keep any custom profiles
                    for profile_id, profile in existing_profiles.items():
                        if profile.get('custom', False):
                            plant_profiles[profile_id] = profile
                
                # Always update the plant profiles
                cls.set('plant_profiles', plant_profiles)
                print("Plant profiles have been reset to defaults")
            elif cls.get(key) is None:
                cls.set(key, value)

    @staticmethod
    def auto_configure_nutrient_components():
        """
        Automatically configure nutrient components based on the available pumps
        """
        # Get all settings
        settings = Settings.query.all()
        if not settings:
            return False
        
        # Get all nutrient pumps
        pumps = Pump.query.filter(Pump.type == 'nutrient').all()
        
        updated_profiles = 0
        total_profiles = len(settings)
        
        for setting in settings:
            # Parse the existing nutrient_components
            current_components = []
            if setting.nutrient_components:
                try:
                    current_components = json.loads(setting.nutrient_components)
                except:
                    current_components = []
            
            # Create new components based on available pumps
            new_components = []
            for pump in pumps:
                if not pump.enabled:
                    continue
                    
                # Skip pumps with no name or nutrient info
                if not pump.name or not pump.nutrient_brand or not pump.nutrient_name:
                    continue
                    
                # Determine the nutrient type based on the name
                nutrient_type = 'other'
                pump_name_lower = pump.name.lower()
                nutrient_name_lower = pump.nutrient_name.lower()
                
                # Detect CalMag/Cal-Mag type
                if ('cal' in pump_name_lower and 'mag' in pump_name_lower) or \
                   ('cal' in nutrient_name_lower and 'mag' in nutrient_name_lower) or \
                   ('calcium' in pump_name_lower and 'magnesium' in pump_name_lower) or \
                   ('calcium' in nutrient_name_lower and 'magnesium' in nutrient_name_lower):
                    nutrient_type = 'calmag'
                # Detect Micro type
                elif 'micro' in pump_name_lower or 'micro' in nutrient_name_lower:
                    nutrient_type = 'micro'
                # Detect Grow type (high nitrogen)
                elif ('grow' in pump_name_lower or 'grow' in nutrient_name_lower or 
                      'veg' in pump_name_lower or 'veg' in nutrient_name_lower):
                    nutrient_type = 'grow'
                # Detect Bloom type (high phosphorus/potassium)
                elif ('bloom' in pump_name_lower or 'bloom' in nutrient_name_lower or 
                      'flower' in pump_name_lower or 'flower' in nutrient_name_lower):
                    nutrient_type = 'bloom'
                
                # Add the component
                new_components.append({
                    'pump_id': pump.id,
                    'name': pump.name,
                    'nutrient_type': nutrient_type,
                    'ml_per_liter': 1.0  # Default dosage
                })
            
            # Check if components need updating
            components_changed = False
            
            # If count changed, definitely update
            if len(current_components) != len(new_components):
                components_changed = True
            else:
                # Even if count is the same, check if content has changed
                # Create a map of current components by pump_id for easy comparison
                current_comp_map = {comp.get('pump_id'): comp for comp in current_components if 'pump_id' in comp}
                
                # Check if any new components differ from current ones
                for new_comp in new_components:
                    pump_id = new_comp.get('pump_id')
                    if pump_id not in current_comp_map:
                        # New pump not in current components
                        components_changed = True
                        break
                        
                    current_comp = current_comp_map[pump_id]
                    # Check if name or nutrient_type has changed
                    if (current_comp.get('name') != new_comp.get('name') or 
                        current_comp.get('nutrient_type') != new_comp.get('nutrient_type')):
                        components_changed = True
                        break
            
            # Update if components changed
            if components_changed:
                # Preserve ml_per_liter settings from existing components when possible
                for new_comp in new_components:
                    for curr_comp in current_components:
                        if (curr_comp.get('pump_id') == new_comp.get('pump_id') and 
                            'ml_per_liter' in curr_comp):
                            new_comp['ml_per_liter'] = curr_comp['ml_per_liter']
                            break
                
                setting.nutrient_components = json.dumps(new_components)
                updated_profiles += 1
        
        if updated_profiles > 0:
            db.session.commit()
            return f"Updated {updated_profiles} of {total_profiles} profiles"
        
        return "No profiles needed updating" 