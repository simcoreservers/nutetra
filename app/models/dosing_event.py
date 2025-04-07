from app import db
from datetime import datetime

class DosingEvent(db.Model):
    __tablename__ = 'dosing_events'
    
    id = db.Column(db.Integer, primary_key=True)
    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id'), nullable=False)
    amount_ml = db.Column(db.Float, nullable=False)
    duration_ms = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100), nullable=False)  # 'ph_high', 'ph_low', 'ec_low', 'manual'
    sensor_before = db.Column(db.Float, nullable=True)  # Sensor reading before dosing
    sensor_after = db.Column(db.Float, nullable=True)   # Sensor reading after dosing
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to pump
    pump = db.relationship('Pump', backref=db.backref('events', lazy=True))
    
    def __repr__(self):
        return f'<DosingEvent pump:{self.pump_id} amount:{self.amount_ml}ml reason:{self.reason}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'pump_id': self.pump_id,
            'pump_name': self.pump.name if self.pump else 'Unknown',
            'amount_ml': self.amount_ml,
            'duration_ms': self.duration_ms,
            'reason': self.reason,
            'sensor_before': self.sensor_before,
            'sensor_after': self.sensor_after,
            'timestamp': self.timestamp.isoformat()
        }
    
    @staticmethod
    def get_recent(limit=10):
        """Get the most recent dosing events"""
        return DosingEvent.query.order_by(
            DosingEvent.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_for_pump(pump_id, limit=50):
        """Get dosing history for a specific pump"""
        return DosingEvent.query.filter_by(
            pump_id=pump_id
        ).order_by(
            DosingEvent.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    def log_event(pump_id, amount_ml, duration_ms, reason, sensor_before=None, sensor_after=None):
        """Log a new dosing event"""
        event = DosingEvent(
            pump_id=pump_id,
            amount_ml=amount_ml,
            duration_ms=duration_ms,
            reason=reason,
            sensor_before=sensor_before,
            sensor_after=sensor_after
        )
        db.session.add(event)
        db.session.commit()
        return event 