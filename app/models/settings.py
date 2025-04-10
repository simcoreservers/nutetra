from app import db
import json
from app.models.pump import Pump
from app.models.nutrient import NutrientProduct, NutrientBrand

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
            },
            'cannabis': {
                'name': 'Cannabis',
                'description': 'Optimized weekly schedule for cannabis cultivation',
                'ph_setpoint': 6.0,
                'ph_buffer': 0.2,
                'ec_setpoint': 1200,  # Base EC that will be adjusted per growth stage
                'ec_buffer': 150,
                'temp_min': 21.0,
                'temp_max': 27.0,
                'nutrient_components': [],
                'custom': False,
                'current_week': 1,  # Track the current grow week
                'total_weeks': 12,  # Total grow cycle length
                'nutrient_ratios': {
                    'grow': 1.0,    # Default ratio if no weekly schedule
                    'bloom': 1.0,   # Default ratio if no weekly schedule
                    'micro': 1.0,   # Default ratio if no weekly schedule
                    'calmag': 1.0   # Default ratio if no weekly schedule
                },
                'weekly_schedules': {
                    '1': {  # Seedling - Week 1
                        'ec_setpoint': 500,
                        'nutrient_ratios': {
                            'grow': 1.0,    # Balanced nitrogen
                            'bloom': 0.0,   # No bloom nutrients
                            'micro': 0.5,   # Low micronutrients
                            'calmag': 0.25  # Low calcium/magnesium
                        }
                    },
                    '2': {  # Seedling - Week 2
                        'ec_setpoint': 700,
                        'nutrient_ratios': {
                            'grow': 1.5,    # Higher nitrogen
                            'bloom': 0.0,   # No bloom nutrients
                            'micro': 0.75,  # Increased micronutrients
                            'calmag': 0.5   # Increased calcium/magnesium
                        }
                    },
                    '3': {  # Vegetative - Week 3
                        'ec_setpoint': 900,
                        'nutrient_ratios': {
                            'grow': 2.0,    # High nitrogen for vegetative growth
                            'bloom': 0.25,  # Very low bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.0   # Full calcium/magnesium
                        }
                    },
                    '4': {  # Vegetative - Week 4
                        'ec_setpoint': 1000,
                        'nutrient_ratios': {
                            'grow': 2.0,    # High nitrogen for vegetative growth
                            'bloom': 0.5,   # Low bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.0   # Full calcium/magnesium
                        }
                    },
                    '5': {  # Vegetative - Week 5
                        'ec_setpoint': 1100,
                        'nutrient_ratios': {
                            'grow': 2.0,    # High nitrogen for vegetative growth
                            'bloom': 0.5,   # Low bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.0   # Full calcium/magnesium
                        }
                    },
                    '6': {  # Pre-Flower - Week 6
                        'ec_setpoint': 1100,
                        'nutrient_ratios': {
                            'grow': 1.5,    # Reduced nitrogen
                            'bloom': 1.0,   # Increased bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.0   # Full calcium/magnesium
                        }
                    },
                    '7': {  # Early Flower - Week 7
                        'ec_setpoint': 1200,
                        'nutrient_ratios': {
                            'grow': 1.0,    # Reduced nitrogen
                            'bloom': 1.5,   # Increased bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.5   # Increased calcium for flowering
                        }
                    },
                    '8': {  # Mid Flower - Week 8
                        'ec_setpoint': 1400,
                        'nutrient_ratios': {
                            'grow': 0.5,    # Lower nitrogen
                            'bloom': 2.0,   # High bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.5   # High calcium/magnesium
                        }
                    },
                    '9': {  # Mid Flower - Week 9
                        'ec_setpoint': 1400,
                        'nutrient_ratios': {
                            'grow': 0.5,    # Lower nitrogen
                            'bloom': 2.0,   # High bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.5   # High calcium/magnesium
                        }
                    },
                    '10': {  # Late Flower - Week 10
                        'ec_setpoint': 1300,
                        'nutrient_ratios': {
                            'grow': 0.25,   # Very low nitrogen
                            'bloom': 2.0,   # High bloom nutrients
                            'micro': 1.0,   # Full micronutrients
                            'calmag': 1.0   # Full calcium/magnesium
                        }
                    },
                    '11': {  # Late Flower - Week 11
                        'ec_setpoint': 1200,
                        'nutrient_ratios': {
                            'grow': 0.0,    # No nitrogen
                            'bloom': 1.5,   # Reduced bloom nutrients
                            'micro': 0.5,   # Reduced micronutrients
                            'calmag': 0.5   # Reduced calcium/magnesium
                        }
                    },
                    '12': {  # Flush - Week 12
                        'ec_setpoint': 400,
                        'nutrient_ratios': {
                            'grow': 0.0,    # No nutrients during flush
                            'bloom': 0.0,   # No nutrients during flush
                            'micro': 0.0,   # No nutrients during flush
                            'calmag': 0.0   # No nutrients during flush
                        }
                    }
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
        # Get all plant profiles
        plant_profiles = Settings.get('plant_profiles', {})
        if not plant_profiles:
            return "No plant profiles found"
        
        # Get all nutrient pumps
        pumps = Pump.query.filter(Pump.type == 'nutrient').all()
        
        updated_profiles = 0
        total_profiles = len(plant_profiles)
        
        for profile_id, profile in plant_profiles.items():
            # Parse the existing nutrient_components
            current_components = profile.get('nutrient_components', [])
            
            # Create new components based on available pumps
            new_components = []
            for pump in pumps:
                if not pump.enabled:
                    continue
                    
                # Skip pumps with no name or nutrient info
                if not pump.name or not pump.nutrient_brand or not pump.nutrient_name:
                    continue
                    
                # Default nutrient type if nothing else is found
                nutrient_type = 'other'
                
                # Get the nutrient product from the database
                brand = NutrientBrand.query.filter_by(name=pump.nutrient_brand).first()
                if brand:
                    # Find the product for this brand
                    product = NutrientProduct.query.filter_by(brand_id=brand.id, name=pump.nutrient_name).first()
                    
                    # Get the nutrient type from the product if available
                    if product and product.nutrient_type:
                        nutrient_type = product.nutrient_type
                    else:
                        # Fall back to name-based detection if product not found or nutrient_type not set
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
                              'gro' in pump_name_lower or 'gro' in nutrient_name_lower or 
                              'veg' in pump_name_lower or 'veg' in nutrient_name_lower):
                            nutrient_type = 'grow'
                        # Detect Bloom type (high phosphorus/potassium)
                        elif ('bloom' in pump_name_lower or 'bloom' in nutrient_name_lower or 
                              'flower' in pump_name_lower or 'flower' in nutrient_name_lower):
                            nutrient_type = 'bloom'
                else:
                    # If no brand found, fall back to name-based detection
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
                          'gro' in pump_name_lower or 'gro' in nutrient_name_lower or 
                          'veg' in pump_name_lower or 'veg' in nutrient_name_lower):
                        nutrient_type = 'grow'
                    # Detect Bloom type (high phosphorus/potassium)
                    elif ('bloom' in pump_name_lower or 'bloom' in nutrient_name_lower or 
                          'flower' in pump_name_lower or 'flower' in nutrient_name_lower):
                        nutrient_type = 'bloom'
            
                # Set dosing order based on nutrient type
                dosing_order = {
                    'calmag': 1,  # Cal-mag supplements go first
                    'micro': 2,   # Micro/trace nutrients second
                    'grow': 3,    # Grow nutrients third
                    'bloom': 4,   # Bloom nutrients last
                    'other': 5    # Anything else at the end
                }.get(nutrient_type, 5)
                
                # Get the appropriate ratio from profile's nutrient_ratios
                # Default to 1.0 if nutrient_ratios is not defined or doesn't have this type
                default_ratio = 1.0
                profile_ratios = None
                
                # Check if this profile has weekly schedules and a current week
                if 'weekly_schedules' in profile and 'current_week' in profile:
                    current_week = str(profile['current_week'])
                    if current_week in profile.get('weekly_schedules', {}):
                        weekly_schedule = profile['weekly_schedules'][current_week]
                        # Use the weekly schedule's nutrient ratios
                        profile_ratios = weekly_schedule.get('nutrient_ratios', {})
                        
                        # Also update the EC setpoint for this profile if specified in the weekly schedule
                        if 'ec_setpoint' in weekly_schedule:
                            profile['ec_setpoint'] = weekly_schedule['ec_setpoint']
                
                # If no weekly schedule found or not using weekly schedules, use the default profile ratios
                if not profile_ratios:
                    profile_ratios = profile.get('nutrient_ratios', {})
                
                # Default to the type-specific ratio if available, otherwise use 1.0
                ratio = profile_ratios.get(nutrient_type, default_ratio)
                
                # Add the component
                new_components.append({
                    'pump_id': pump.id,
                    'pump_name': pump.name,
                    'nutrient_type': nutrient_type,
                    'dosing_order': dosing_order,
                    'ratio': ratio  # Use profile-specific ratio
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
                    # Check if pump_name or nutrient_type has changed
                    if (current_comp.get('pump_name') != new_comp.get('pump_name') or 
                        current_comp.get('nutrient_type') != new_comp.get('nutrient_type')):
                        components_changed = True
                        break
            
            # Update if components changed
            if components_changed:
                # Create a map of existing components by pump_id for easier ratio preservation
                current_comp_map = {comp.get('pump_id'): comp for comp in current_components if 'pump_id' in comp}
                
                # Preserve ratio settings from existing components when possible
                for new_comp in new_components:
                    pump_id = new_comp.get('pump_id')
                    if pump_id in current_comp_map:
                        # Found an existing component for this pump, preserve its ratio
                        curr_comp = current_comp_map[pump_id]
                        if 'ratio' in curr_comp:
                            new_comp['ratio'] = curr_comp['ratio']
                        elif 'ml_per_liter' in curr_comp:
                            # Handle legacy components with ml_per_liter instead of ratio
                            new_comp['ratio'] = curr_comp['ml_per_liter']
                
                # Sort components by dosing_order to ensure proper sequence
                new_components.sort(key=lambda comp: comp.get('dosing_order', 99))
                
                # Update the nutrient_components in the profile
                profile['nutrient_components'] = new_components
                updated_profiles += 1
        
        # Update the plant_profiles setting if any profiles were updated
        if updated_profiles > 0:
            Settings.set('plant_profiles', plant_profiles)
            return f"Updated {updated_profiles} of {total_profiles} profiles"
        
        return "No profiles needed updating" 