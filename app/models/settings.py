from app import db
import json

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
    def initialize_defaults(cls):
        """Initialize default settings"""
        
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
        
        defaults = {
        # pH settings
        'ph_setpoint': 6.0,
        'ph_buffer': 0.2,
        'ph_check_interval': 300,  # seconds
        'ph_dose_amount': 1.0,     # ml
        'ph_dose_wait_time': 60,   # seconds to wait after dosing
        
        # EC settings
        'ec_setpoint': 1350,
        'ec_buffer': 150,
        'ec_check_interval': 300,  # seconds
        'ec_dose_amount': 5.0,     # ml
        'ec_dose_wait_time': 60,   # seconds to wait after dosing
        
        # Temperature settings
        'temp_check_interval': 300,  # seconds
        'temp_min_alert': 18.0,      # °C
        'temp_max_alert': 30.0,      # °C
        
        # Notification settings
        'notifications_enabled': True,
        'email_notifications': False,
        'email_address': '',
        'sms_notifications': False,
        'phone_number': '',
        
        # System settings
        'logging_interval': 300,  # seconds
        'auto_dosing_enabled': True,
        'night_mode_enabled': False,
        'night_mode_start': '22:00',
        'night_mode_end': '06:00',
        
        # UI settings
        'dark_mode': True,
        'temp_target': 25.0,
        'temp_buffer': 2.0,
        'chart_points': 50,
        'refresh_interval': 10,  # seconds
        }
        
        default_values = defaults.copy()
        
        for key, value in default_values.items():
            if Settings.get(key) is None:
                Settings.set(key, value) 

    @staticmethod
    def auto_configure_nutrient_components():
        """
        Automatically configure nutrient components for all default profiles
        based on available nutrient pumps
        """
        from app.models.pump import Pump
        
        # Get all enabled nutrient pumps
        nutrient_pumps = Pump.query.filter(
            Pump.type == 'nutrient',
            Pump.enabled == True
        ).all()
        
        # Get all plant profiles
        plant_profiles = Settings.get('plant_profiles', {})
        
        # Track if we've made changes
        profiles_updated = False
        
        # Nutrient type mapping based on name patterns
        def get_nutrient_type(pump):
            name = pump.nutrient_name.lower() if pump.nutrient_name else pump.name.lower()
            if any(term in name for term in ['grow', 'veg', 'vegetative']):
                return 'grow'
            elif any(term in name for term in ['bloom', 'flower', 'fruit']):
                return 'bloom'
            elif any(term in name for term in ['micro', 'trace']):
                return 'micro'
            elif any(term in name for term in ['cal', 'mag', 'calcium', 'magnesium']):
                return 'calmag'
            else:
                # Default to grow if we can't determine
                return 'grow'
        
        # Check for incompatible nutrients
        def check_incompatibility(pumps):
            incompatibilities = []
            
            # Example incompatibility check: calcium-containing products with phosphates
            calcium_pumps = [p for p in pumps if 'cal' in (p.nutrient_name or '').lower()]
            phosphate_pumps = [p for p in pumps if 'phos' in (p.nutrient_name or '').lower()]
            
            if calcium_pumps and phosphate_pumps:
                incompatibilities.append({
                    'type': 'mixing',
                    'message': 'Calcium products should not be mixed directly with phosphates',
                    'pumps': [{'id': p.id, 'name': p.name} for p in calcium_pumps + phosphate_pumps]
                })
            
            return incompatibilities
        
        # Check for incompatibilities and store them
        incompatibilities = check_incompatibility(nutrient_pumps)
        if incompatibilities:
            Settings.set('nutrient_incompatibilities', incompatibilities)
        else:
            Settings.set('nutrient_incompatibilities', [])
        
        # Process each default profile
        for profile_id, profile in plant_profiles.items():
            # Skip custom profiles
            if profile.get('custom', True):
                continue
            
            # Get nutrient ratios for this profile
            nutrient_ratios = profile.get('nutrient_ratios', {})
            if not nutrient_ratios:
                continue
            
            # Create new components based on available pumps
            new_components = []
            
            # Define nutrient type order (for dosing sequence)
            type_order = {
                'calmag': 1,  # Cal-mag supplements go first (standard practice)
                'micro': 2,   # Micro/trace nutrients second
                'grow': 3,    # Grow nutrients third
                'bloom': 4    # Bloom nutrients last
            }
            
            for pump in nutrient_pumps:
                # Only include enabled pumps
                if not pump.enabled:
                    continue
                    
                nutrient_type = get_nutrient_type(pump)
                
                # Get the ratio for this nutrient type from the profile
                ratio = nutrient_ratios.get(nutrient_type, 1.0)
                
                # Set dosing order for this component
                order = type_order.get(nutrient_type, 99)
                
                # Add as a component
                new_components.append({
                    'pump_id': pump.id,
                    'pump_name': pump.name,
                    'ratio': ratio,
                    'nutrient_type': nutrient_type,  # Store the type for reference
                    'dosing_order': order           # Add order for sorting
                })
            
            # Sort components by dosing order
            new_components.sort(key=lambda x: x.get('dosing_order', 99))
            
            # Update the profile if we have components and they're different from what's there
            if new_components and (len(new_components) != len(profile.get('nutrient_components', []))):
                profile['nutrient_components'] = new_components
                profiles_updated = True
        
        # Calculate dosing amounts in ml/L for each profile and component
        for profile_id, profile in plant_profiles.items():
            if 'nutrient_components' in profile and profile['nutrient_components']:
                # Calculate total ratio sum
                total_ratio = sum(comp.get('ratio', 0) for comp in profile['nutrient_components'])
                
                if total_ratio > 0:
                    # Base dosing calculation on EC target
                    # This is a simplification - in reality, EC response varies by nutrient
                    # A typical value might be around 2-4 ml/L for a ~1500 µS/cm target
                    ec_target = profile.get('ec_setpoint', 1350)
                    
                    # Factor to convert EC to ml/L (approximation)
                    # Higher EC = more nutrients
                    base_dose_ml_per_liter = ec_target / 1350 * 3.0  # ~3ml/L at EC 1350
                    
                    # Calculate individual doses
                    for comp in profile['nutrient_components']:
                        if total_ratio > 0:
                            # Calculate this component's portion of the base dose
                            ratio = comp.get('ratio', 0)
                            dosing_ml_per_liter = (ratio / total_ratio) * base_dose_ml_per_liter
                            
                            # Round to 2 decimal places for display
                            comp['dosing_ml_per_liter'] = round(dosing_ml_per_liter, 2)
                            
                            # Also calculate ml per gallon for US users (1 gal ≈ 3.785 L)
                            comp['dosing_ml_per_gallon'] = round(dosing_ml_per_liter * 3.785, 2)
        
        # Save profiles if updated
        if profiles_updated:
            Settings.set('plant_profiles', plant_profiles)
        
        return {
            'updated': profiles_updated,
            'pumps_found': len(nutrient_pumps),
            'incompatibilities': incompatibilities
        } 