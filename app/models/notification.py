from app import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'info', 'warning', 'error', 'success'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.type}>'
    
    def to_dict(self):
        """Convert notification to dictionary for API responses"""
        return {
            'id': self.id,
            'message': self.message,
            'type': self.type,
            'timestamp': self.timestamp.isoformat(),
            'is_read': self.is_read
        }
    
    @staticmethod
    def create(message, type='info'):
        """Create a new notification"""
        notification = Notification(message=message, type=type)
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def get_all(limit=50, include_read=False):
        """Get all notifications, newest first"""
        query = Notification.query
        if not include_read:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def mark_read(notification_id):
        """Mark a notification as read"""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_read():
        """Mark all notifications as read"""
        Notification.query.update({Notification.is_read: True})
        db.session.commit()
        return True 