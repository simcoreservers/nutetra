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

    @classmethod
    def auto_configure_nutrient_components(cls, forced=False):
        """Automatically configures nutrient components based on available pumps."""
        components_changed = False
        message = "No changes to nutrient components were needed."
        
        # Get all enabled nutrient pumps
        pumps = Pump.query.filter(
            Pump.enabled == True,
            Pump.type.in_(['nutrient', 'ph_up', 'ph_down'])
        ).all()
        
        # Get existing profiles
        plant_profiles = cls.get('plant_profiles', {})
        
        # Loop through all profiles and update their components
        for profile_name, profile in plant_profiles.items():
            profile_components_changed = False
            components = profile.get('nutrient_components', [])
            
            # Check if profile has weekly schedules and current week
            has_weekly_schedule = bool(profile.get('weekly_schedules', {}))
            current_week = str(profile.get('current_week', 1))
            
            # For weekly schedule profiles, get ratio from current week's schedule
            weekly_schedule_applied = None
            if has_weekly_schedule:
                weekly_schedules = profile.get('weekly_schedules', {})
                current_schedule = weekly_schedules.get(current_week, {})
                
                # Store the current week for tracking
                weekly_schedule_applied = current_week
                
                # Check if weekly schedule has nutrient ratios
                if 'nutrient_ratios' in current_schedule:
                    nutrient_ratios = current_schedule.get('nutrient_ratios', {})
                else:
                    nutrient_ratios = profile.get('nutrient_ratios', {})
                    
                # Update EC setpoint if specified in weekly schedule
                if 'ec_target' in current_schedule:
                    profile['ec_target'] = current_schedule.get('ec_target')
                    profile_components_changed = True
            else:
                # Use profile's standard nutrient ratios
                nutrient_ratios = profile.get('nutrient_ratios', {})
            
            # Check if any component doesn't have the current weekly schedule applied
            if has_weekly_schedule and components:
                weekly_schedule_check = [comp.get('weekly_schedule_applied') == current_week for comp in components]
                if not all(weekly_schedule_check) or forced:
                    # Force update if weekly schedule has changed
                    profile_components_changed = True
            
            # Get all nutrient types from available pumps
            nutrient_types = {}
            
            for pump in pumps:
                if pump.type == 'nutrient':
                    # Only use the nutrient type from the product database
                    nutrient_type = 'other'  # Default value if not found
                    
                    if pump.nutrient_brand and pump.nutrient_name:
                        # Try to find the product in the database
                        nutrient_product = NutrientProduct.query.join(NutrientBrand).filter(
                            NutrientBrand.name == pump.nutrient_brand,
                            NutrientProduct.name == pump.nutrient_name
                        ).first()
                        
                        # If found and has a nutrient_type, use that
                        if nutrient_product and nutrient_product.nutrient_type:
                            nutrient_type = nutrient_product.nutrient_type
                        # If not explicitly defined in the database, determine type based on name
                        else:
                            nutrient_name_lower = pump.nutrient_name.lower() if pump.nutrient_name else ''
                            
                            # Determine type based on generic terms in the name
                            if 'grow' in nutrient_name_lower or 'gro' in nutrient_name_lower:
                                nutrient_type = 'grow'
                            # Check for bloom nutrients
                            elif 'bloom' in nutrient_name_lower:
                                nutrient_type = 'bloom'
                            # Check for micro nutrients
                            elif 'micro' in nutrient_name_lower:
                                nutrient_type = 'micro'
                            # Check for cal-mag nutrients
                            elif ('cal' in nutrient_name_lower and 'mag' in nutrient_name_lower) or 'calmag' in nutrient_name_lower:
                                nutrient_type = 'calmag'
                    
                    # Skip if pump is a duplicate of an existing type
                    if nutrient_type in nutrient_types:
                        continue
                    
                    nutrient_types[nutrient_type] = {
                        'pump_id': pump.id,
                        'pump_name': pump.name,
                        'nutrient_name': pump.nutrient_name,
                        'type': nutrient_type
                    }
            
            # Get dosing order
            dosing_order = cls.get('dosing_order', ["calmag", "micro", "grow", "bloom", "ph_down", "ph_up"])
            
            # Create new components list
            new_components = []
            
            # Add pH components first (always keep these)
            ph_components = [comp for comp in components if comp.get('type') in ['ph_down', 'ph_up']]
            for comp in ph_components:
                new_components.append(comp)
            
            # Add nutrient components with correct ratios
            for nutrient_type, pump_info in nutrient_types.items():
                # Find existing component with this type
                existing_comp = next((comp for comp in components 
                                    if comp.get('type') == nutrient_type), None)
                
                # Create or update component
                if existing_comp:
                    # For weekly schedule profiles, use schedule ratios instead of preserving old ones
                    if has_weekly_schedule:
                        ratio = nutrient_ratios.get(nutrient_type, 1.0)
                        if existing_comp.get('ratio') != ratio or existing_comp.get('weekly_schedule_applied') != current_week:
                            existing_comp['ratio'] = ratio
                            existing_comp['weekly_schedule_applied'] = current_week
                            profile_components_changed = True
                    
                    existing_comp['pump_id'] = pump_info['pump_id']
                    existing_comp['pump_name'] = pump_info['pump_name']
                    existing_comp['nutrient_name'] = pump_info['nutrient_name']
                    new_components.append(existing_comp)
                else:
                    # Create new component with default ratio from profile
                    ratio = nutrient_ratios.get(nutrient_type, 1.0)
                    new_comp = {
                        'type': nutrient_type,
                        'pump_id': pump_info['pump_id'],
                        'pump_name': pump_info['pump_name'],
                        'nutrient_name': pump_info['nutrient_name'],
                        'ratio': ratio,
                        'weekly_schedule_applied': weekly_schedule_applied if has_weekly_schedule else None
                    }
                    new_components.append(new_comp)
                    profile_components_changed = True
            
            # Apply dosing order sort
            def sort_key(comp):
                type_val = comp.get('type')
                if type_val in dosing_order:
                    return dosing_order.index(type_val)
                return 999  # Place unknown types at the end
                
            new_components.sort(key=sort_key)
            
            # Update components if they've changed
            if profile_components_changed or forced or len(new_components) != len(components):
                # Mark all components as having the current weekly schedule applied
                if has_weekly_schedule:
                    for comp in new_components:
                        comp['weekly_schedule_applied'] = current_week
                
                profile['nutrient_components'] = new_components
                components_changed = True
            
        # Save changes if needed
        if components_changed or forced:
            cls.set('plant_profiles', plant_profiles)
            message = "Nutrient components updated successfully."
        
        return message 