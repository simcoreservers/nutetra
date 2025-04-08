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
    
    @staticmethod
    def initialize_defaults():
        """Set default settings if they don't exist"""
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
            'chart_points': 50,
            'refresh_interval': 10,  # seconds
        }
        
        for key, value in defaults.items():
            if Settings.get(key) is None:
                Settings.set(key, value) 