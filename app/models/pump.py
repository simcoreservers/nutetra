from app import db

class Pump(db.Model):
    __tablename__ = 'pumps'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'ph_up', 'ph_down', 'nutrient_a', 'nutrient_b', etc.
    gpio_pin = db.Column(db.Integer, nullable=False)
    flow_rate = db.Column(db.Float, nullable=False)  # ml per second
    enabled = db.Column(db.Boolean, default=True)
    
    # New fields for nutrient information
    nutrient_brand = db.Column(db.String(50), nullable=True)
    nutrient_name = db.Column(db.String(100), nullable=True)
    nitrogen_pct = db.Column(db.Float, nullable=True)  # N percentage
    phosphorus_pct = db.Column(db.Float, nullable=True)  # P percentage
    potassium_pct = db.Column(db.Float, nullable=True)  # K percentage
    
    def __repr__(self):
        return f'<Pump {self.id}: {self.name} ({self.type})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'gpio_pin': self.gpio_pin,
            'flow_rate': self.flow_rate,
            'enabled': self.enabled,
            'nutrient_brand': self.nutrient_brand,
            'nutrient_name': self.nutrient_name,
            'nitrogen_pct': self.nitrogen_pct,
            'phosphorus_pct': self.phosphorus_pct,
            'potassium_pct': self.potassium_pct
        }
    
    def calculate_dosing_time(self, amount_ml):
        """Calculate how long the pump should run to dispense a specific amount"""
        if self.flow_rate <= 0:
            return 0
        return int((amount_ml / self.flow_rate) * 1000)  # Convert to milliseconds
    
    @staticmethod
    def get_by_type(pump_type):
        """Get all pumps of a specific type"""
        return Pump.query.filter_by(type=pump_type, enabled=True).all()
    
    @staticmethod
    def get_enabled():
        """Get all enabled pumps"""
        return Pump.query.filter_by(enabled=True).all()
    
    @staticmethod
    def initialize_defaults():
        """Set up default pumps if none exist"""
        # Check if pH pumps exist
        ph_up_exists = Pump.query.filter_by(type="ph_up").first() is not None
        ph_down_exists = Pump.query.filter_by(type="ph_down").first() is not None
        
        # Always ensure pH pumps exist as they are hardwired
        if not ph_up_exists:
            ph_up = Pump(name="pH Up", type="ph_up", gpio_pin=17, flow_rate=1.0)
            db.session.add(ph_up)
            
        if not ph_down_exists:
            ph_down = Pump(name="pH Down", type="ph_down", gpio_pin=18, flow_rate=1.0)
            db.session.add(ph_down)
        
        # Only add other default pumps if no pumps exist at all
        if Pump.query.count() == 0:
            default_nutrient_pumps = [
                Pump(name="Grow Nutrient", type="nutrient", gpio_pin=22, flow_rate=1.0),
                Pump(name="Bloom Nutrient", type="nutrient", gpio_pin=23, flow_rate=1.0),
                Pump(name="Micro Nutrient", type="nutrient", gpio_pin=24, flow_rate=1.0)
            ]
            
            for pump in default_nutrient_pumps:
                db.session.add(pump)
        
        # Commit any changes made
        if db.session.new:
            db.session.commit() 