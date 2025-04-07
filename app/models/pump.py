from app import db

class Pump(db.Model):
    __tablename__ = 'pumps'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'ph_up', 'ph_down', 'nutrient_a', 'nutrient_b', etc.
    gpio_pin = db.Column(db.Integer, nullable=False)
    flow_rate = db.Column(db.Float, nullable=False)  # ml per second
    enabled = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Pump {self.id}: {self.name} ({self.type})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'gpio_pin': self.gpio_pin,
            'flow_rate': self.flow_rate,
            'enabled': self.enabled
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
        if Pump.query.count() == 0:
            default_pumps = [
                Pump(name="pH Up", type="ph_up", gpio_pin=17, flow_rate=1.0),
                Pump(name="pH Down", type="ph_down", gpio_pin=18, flow_rate=1.0),
                Pump(name="Nutrient A", type="nutrient_a", gpio_pin=22, flow_rate=1.0),
                Pump(name="Nutrient B", type="nutrient_b", gpio_pin=23, flow_rate=1.0),
                Pump(name="Nutrient C", type="nutrient_c", gpio_pin=24, flow_rate=1.0)
            ]
            
            for pump in default_pumps:
                db.session.add(pump)
            
            db.session.commit() 