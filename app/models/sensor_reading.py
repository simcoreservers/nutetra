from app import db
from datetime import datetime

class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    sensor_type = db.Column(db.String(20), nullable=False)  # 'ph', 'ec', 'temp'
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SensorReading {self.sensor_type}: {self.value} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sensor_type': self.sensor_type,
            'value': self.value,
            'timestamp': self.timestamp.isoformat()
        }
    
    @staticmethod
    def get_latest(sensor_type):
        """Get the most recent reading for a specific sensor type"""
        return SensorReading.query.filter_by(
            sensor_type=sensor_type
        ).order_by(
            SensorReading.timestamp.desc()
        ).first()
    
    @staticmethod
    def get_history(sensor_type, limit=100):
        """Get historical readings for a specific sensor type"""
        return SensorReading.query.filter_by(
            sensor_type=sensor_type
        ).order_by(
            SensorReading.timestamp.desc()
        ).limit(limit).all()

    @staticmethod
    def add_reading(sensor_type, value):
        """Add a new sensor reading to the database"""
        reading = SensorReading(sensor_type=sensor_type, value=value)
        db.session.add(reading)
        db.session.commit()
        return reading 