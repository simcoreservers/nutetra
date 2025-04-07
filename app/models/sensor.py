from app import db
from datetime import datetime
from app.models.sensor_reading import SensorReading

class SensorData:
    """
    Class for aggregating sensor data from various sensor readings
    """
    def __init__(self, ph=None, ec=None, temperature=None, timestamp=None):
        self.ph = ph
        self.ec = ec
        self.temperature = temperature
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """
        Convert sensor data to dictionary
        """
        return {
            'ph': self.ph,
            'ec': self.ec,
            'temperature': self.temperature,
            'timestamp': self.timestamp.isoformat()
        }
    
    @staticmethod
    def get_latest():
        """
        Get the latest readings from all sensors
        Returns a SensorData object with the latest values
        """
        ph_reading = SensorReading.get_latest('ph')
        ec_reading = SensorReading.get_latest('ec')
        temp_reading = SensorReading.get_latest('temp')
        
        # Use the most recent timestamp
        timestamps = []
        if ph_reading:
            timestamps.append(ph_reading.timestamp)
        if ec_reading:
            timestamps.append(ec_reading.timestamp)
        if temp_reading:
            timestamps.append(temp_reading.timestamp)
        
        latest_timestamp = max(timestamps) if timestamps else datetime.utcnow()
        
        return SensorData(
            ph=ph_reading.value if ph_reading else None,
            ec=ec_reading.value if ec_reading else None,
            temperature=temp_reading.value if temp_reading else None,
            timestamp=latest_timestamp
        )
    
    @staticmethod
    def get_history(limit=100):
        """
        Get historical readings for all sensors, aligned by timestamp
        Returns a list of SensorData objects
        """
        # Get all readings
        ph_readings = SensorReading.get_history('ph', limit)
        ec_readings = SensorReading.get_history('ec', limit)
        temp_readings = SensorReading.get_history('temp', limit)
        
        # Convert to dictionaries for easy lookup
        ph_dict = {r.timestamp: r.value for r in ph_readings}
        ec_dict = {r.timestamp: r.value for r in ec_readings}
        temp_dict = {r.timestamp: r.value for r in temp_readings}
        
        # Combine all timestamps
        all_timestamps = sorted(
            set(ph_dict.keys()) | set(ec_dict.keys()) | set(temp_dict.keys()),
            reverse=True
        )
        
        # Limit to the requested number of points
        all_timestamps = all_timestamps[:limit]
        
        # Create SensorData objects
        result = []
        for ts in all_timestamps:
            result.append(SensorData(
                ph=ph_dict.get(ts),
                ec=ec_dict.get(ts),
                temperature=temp_dict.get(ts),
                timestamp=ts
            ))
        
        return result
    
    @staticmethod
    def get_range(start_time, end_time):
        """
        Get sensor data for a specific time range
        Returns a list of SensorData objects
        """
        # Get readings within time range
        ph_readings = SensorReading.query.filter(
            SensorReading.sensor_type == 'ph',
            SensorReading.timestamp >= start_time,
            SensorReading.timestamp <= end_time
        ).order_by(SensorReading.timestamp).all()
        
        ec_readings = SensorReading.query.filter(
            SensorReading.sensor_type == 'ec',
            SensorReading.timestamp >= start_time,
            SensorReading.timestamp <= end_time
        ).order_by(SensorReading.timestamp).all()
        
        temp_readings = SensorReading.query.filter(
            SensorReading.sensor_type == 'temp',
            SensorReading.timestamp >= start_time,
            SensorReading.timestamp <= end_time
        ).order_by(SensorReading.timestamp).all()
        
        # Convert to dictionaries for easy lookup
        ph_dict = {r.timestamp: r.value for r in ph_readings}
        ec_dict = {r.timestamp: r.value for r in ec_readings}
        temp_dict = {r.timestamp: r.value for r in temp_readings}
        
        # Combine all timestamps
        all_timestamps = sorted(
            set(ph_dict.keys()) | set(ec_dict.keys()) | set(temp_dict.keys())
        )
        
        # Create SensorData objects
        result = []
        for ts in all_timestamps:
            result.append(SensorData(
                ph=ph_dict.get(ts),
                ec=ec_dict.get(ts),
                temperature=temp_dict.get(ts),
                timestamp=ts
            ))
        
        return result 