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
        
        # Plant profiles
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
                'nutrient_components': [
                    {'pump_id': 1, 'pump_name': 'Nutrient A', 'ratio': 1.0},
                    {'pump_id': 2, 'pump_name': 'Nutrient B', 'ratio': 1.0}
                ],
                'custom': False
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
                'nutrient_components': [
                    {'pump_id': 1, 'pump_name': 'Nutrient A', 'ratio': 1.0},
                    {'pump_id': 2, 'pump_name': 'Nutrient B', 'ratio': 1.0}
                ],
                'custom': False
            },
            'fruiting': {
                'name': 'Fruiting Plants',
                'description': 'Optimal settings for tomatoes, peppers, cucumbers, etc.',
                'ph_setpoint': 6.2,
                'ph_buffer': 0.2,
                'ec_setpoint': 1800,
                'ec_buffer': 150,
                'temp_min': 20.0,
                'temp_max': 30.0,
                'nutrient_components': [
                    {'pump_id': 1, 'pump_name': 'Nutrient A', 'ratio': 1.0},
                    {'pump_id': 2, 'pump_name': 'Nutrient B', 'ratio': 1.0},
                    {'pump_id': 3, 'pump_name': 'Nutrient C', 'ratio': 0.5}
                ],
                'custom': False
            },
            'herbs': {
                'name': 'Herbs',
                'description': 'Optimal settings for basil, cilantro, mint, etc.',
                'ph_setpoint': 5.8,
                'ph_buffer': 0.2,
                'ec_setpoint': 1000,
                'ec_buffer': 150,
                'temp_min': 18.0,
                'temp_max': 26.0,
                'nutrient_components': [
                    {'pump_id': 1, 'pump_name': 'Nutrient A', 'ratio': 1.0},
                    {'pump_id': 2, 'pump_name': 'Nutrient B', 'ratio': 0.8}
                ],
                'custom': False
            },
            'strawberries': {
                'name': 'Strawberries',
                'description': 'Optimal settings for strawberries',
                'ph_setpoint': 5.8,
                'ph_buffer': 0.2,
                'ec_setpoint': 1500,
                'ec_buffer': 150,
                'temp_min': 16.0,
                'temp_max': 24.0,
                'nutrient_components': [
                    {'pump_id': 1, 'pump_name': 'Nutrient A', 'ratio': 1.0},
                    {'pump_id': 2, 'pump_name': 'Nutrient B', 'ratio': 1.0},
                    {'pump_id': 3, 'pump_name': 'Nutrient C', 'ratio': 0.3}
                ],
                'custom': False
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