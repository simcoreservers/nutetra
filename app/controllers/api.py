from flask import Blueprint, jsonify, request
from app.models.sensor_reading import SensorReading
from app.models.dosing_event import DosingEvent
from app.models.settings import Settings
from app.models.pump import Pump
from app.utils.sensor_manager import read_all_sensors, read_sensor, calibrate_ph, calibrate_ec, calibrate_temperature
from app.utils.dosing_manager import activate_pump
import json
from datetime import datetime, timedelta
import random
import os
from ..models.sensor import SensorData
from ..models.notification import Notification
from app.models.nutrient import NutrientBrand, NutrientProduct
from app import db

# Create a blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/sensors', methods=['GET'])
def get_sensors():
    """Get the most recent sensor readings"""
    try:
        # Get the latest readings from the database
        ph = SensorReading.get_latest('ph')
        ec = SensorReading.get_latest('ec')
        temp = SensorReading.get_latest('temp')
        
        return jsonify({
            'success': True,
            'data': {
                'ph': ph.to_dict() if ph else None,
                'ec': ec.to_dict() if ec else None,
                'temp': temp.to_dict() if temp else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sensors/read_now', methods=['POST'])
def read_sensors_now():
    """Take a new reading of all sensors right now"""
    try:
        # Read all sensors
        readings = read_all_sensors()
        
        # Format the results
        result = {}
        for sensor_type, value in readings.items():
            if value is not None:
                result[sensor_type] = value
            else:
                result[sensor_type] = None
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sensors/history/<sensor_type>', methods=['GET'])
def get_sensor_history(sensor_type):
    """Get historical readings for a specific sensor"""
    try:
        # Validate sensor type
        if sensor_type not in ['ph', 'ec', 'temp']:
            return jsonify({
                'success': False,
                'error': f"Invalid sensor type: {sensor_type}"
            }), 400
        
        # Get limit from query parameters or default to 100
        limit = request.args.get('limit', 100, type=int)
        
        # Get historical readings
        readings = SensorReading.get_history(sensor_type, limit)
        
        return jsonify({
            'success': True,
            'data': [reading.to_dict() for reading in readings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/dosing/events', methods=['GET'])
def get_dosing_events():
    """Get recent dosing events"""
    try:
        # Get limit from query parameters or default to 10
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent dosing events
        events = DosingEvent.get_recent(limit)
        
        return jsonify({
            'success': True,
            'data': [event.to_dict() for event in events]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/dosing/pump/<int:pump_id>', methods=['POST'])
def dose_manual(pump_id):
    """Manually activate a pump"""
    try:
        # Get the pump
        pump = Pump.query.get(pump_id)
        if not pump:
            return jsonify({
                'success': False,
                'error': f"Pump with ID {pump_id} not found"
            }), 404
        
        # Get dosing parameters from request
        data = request.get_json() or {}
        amount_ml = data.get('amount_ml')
        duration_ms = data.get('duration_ms')
        
        # If amount_ml is provided, calculate duration
        if amount_ml is not None:
            duration_ms = pump.calculate_dosing_time(float(amount_ml))
        # Otherwise, use the provided duration or default
        else:
            duration_ms = duration_ms or 1000  # Default 1 second
        
        # Activate the pump
        success = activate_pump(
            pump_id=pump_id,
            duration_ms=int(duration_ms),
            reason='manual'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Pump {pump.name} activated successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Failed to activate pump"
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get all settings"""
    try:
        settings = Settings.get_all()
        
        return jsonify({
            'success': True,
            'data': settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        # Update each setting
        for key, value in data.items():
            Settings.set(key, value)
        
        return jsonify({
            'success': True,
            'message': "Settings updated successfully"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/pumps', methods=['GET'])
def get_pumps():
    """Get all pumps"""
    try:
        pumps = Pump.query.all()
        
        return jsonify({
            'success': True,
            'data': [pump.to_dict() for pump in pumps]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/pumps', methods=['POST'])
def create_pump():
    """Create a new pump"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'type', 'gpio_pin', 'flow_rate']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        # Prevent creating pH pumps as they are hardwired
        if data['type'] in ['ph_up', 'ph_down']:
            return jsonify({
                'success': False,
                'error': "pH pumps are hardwired and cannot be created. You can only create nutrient pumps."
            }), 403
                
        # Ensure the type is 'nutrient'
        if data['type'] != 'nutrient':
            data['type'] = 'nutrient'
        
        # Create new pump
        new_pump = Pump(
            name=data['name'],
            type=data['type'],
            gpio_pin=data['gpio_pin'],
            flow_rate=data['flow_rate'],
            enabled=data.get('enabled', True),
            nutrient_brand=data.get('nutrient_brand'),
            nutrient_name=data.get('nutrient_name'),
            nitrogen_pct=data.get('nitrogen_pct'),
            phosphorus_pct=data.get('phosphorus_pct'),
            potassium_pct=data.get('potassium_pct')
        )
        
        # Save to database
        db.session.add(new_pump)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Pump created successfully",
            'data': new_pump.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/pumps/<int:pump_id>', methods=['PUT'])
def update_pump(pump_id):
    from app.models.settings import Settings
    
    pump = Pump.query.get(pump_id)
    if not pump:
        return jsonify({'error': 'Pump not found'}), 404
    
    data = request.json
    
    # For pH pumps, only the enabled state can be modified
    if pump.type in ['ph_up', 'ph_down']:
        if 'enabled' in data:
            pump.enabled = bool(data['enabled'])
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': f'pH pump {pump_id} {"enabled" if pump.enabled else "disabled"}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Only the enabled state can be modified for pH pumps'
            }), 403
    
    # Track if nutrient information has changed to trigger profile updates
    nutrient_changed = False
    
    # For normal nutrient pumps, check values
    if 'name' in data and data['name'] != pump.name:
        pump.name = data['name']
        nutrient_changed = True
    
    if 'gpio_pin' in data:
        new_pin = data['gpio_pin']
        # Check if this pin is already in use by another pump
        existing_pump = Pump.query.filter(Pump.gpio_pin == new_pin, Pump.id != pump_id).first()
        if existing_pump:
            return jsonify({
                'status': 'error',
                'message': f'GPIO pin {new_pin} is already in use by pump: {existing_pump.name}'
            }), 400
        pump.gpio_pin = new_pin
    
    # Update other fields if provided
    if 'enabled' in data:
        pump.enabled = bool(data['enabled'])
    
    if 'nutrient_brand' in data and data['nutrient_brand'] != pump.nutrient_brand:
        pump.nutrient_brand = data['nutrient_brand']
        nutrient_changed = True
    
    if 'nutrient_name' in data and data['nutrient_name'] != pump.nutrient_name:
        pump.nutrient_name = data['nutrient_name'] 
        nutrient_changed = True
    
    if 'nitrogen_pct' in data and data['nitrogen_pct'] != pump.nitrogen_pct:
        pump.nitrogen_pct = data['nitrogen_pct']
        nutrient_changed = True
    
    if 'phosphorus_pct' in data and data['phosphorus_pct'] != pump.phosphorus_pct:
        pump.phosphorus_pct = data['phosphorus_pct']
        nutrient_changed = True
    
    if 'potassium_pct' in data and data['potassium_pct'] != pump.potassium_pct:
        pump.potassium_pct = data['potassium_pct']
        nutrient_changed = True
    
    # Always update type to 'nutrient' for any legacy nutrient pump types
    if pump.type.startswith('nutrient_'):
        pump.type = 'nutrient'
    
    # Commit the changes
    db.session.commit()
    
    # If nutrient information changed, update all profiles
    if nutrient_changed:
        update_result = Settings.auto_configure_nutrient_components()
        return jsonify({
            'success': True,
            'message': f'Pump {pump.name} updated and profiles reconfigured',
            'profile_update': update_result,
            'data': pump.to_dict()
        })
    
    return jsonify({
        'success': True,
        'message': f'Pump {pump.name} updated',
        'data': pump.to_dict()
    })

@api_bp.route('/pumps/<int:pump_id>', methods=['GET'])
def get_pump(pump_id):
    """Get a single pump by ID"""
    try:
        pump = Pump.query.get(pump_id)
        if not pump:
            return jsonify({
                'success': False,
                'error': f"Pump with ID {pump_id} not found"
            }), 404
        
        return jsonify({
            'success': True,
            'data': pump.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/pumps/<int:pump_id>', methods=['DELETE'])
def delete_pump(pump_id):
    """Delete a pump"""
    try:
        from app.models.settings import Settings
        
        pump = Pump.query.get(pump_id)
        if not pump:
            return jsonify({
                'success': False,
                'error': f"Pump with ID {pump_id} not found"
            }), 404
        
        # Prevent deleting pH pumps as they are hardwired
        if pump.type in ['ph_up', 'ph_down']:
            return jsonify({
                'success': False,
                'error': "pH pumps are hardwired and cannot be deleted"
            }), 403
        
        # Delete the pump
        db.session.delete(pump)
        db.session.commit()
        
        # Update all profiles to reflect the deleted pump
        update_result = Settings.auto_configure_nutrient_components()
        
        return jsonify({
            'success': True,
            'message': f"Pump '{pump.name}' deleted successfully",
            'profile_update': update_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/calibration/ph', methods=['POST'])
def calibrate_ph_endpoint():
    """Calibrate the pH sensor"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        point = data.get('point')
        value = data.get('value')
        
        if not point:
            return jsonify({
                'success': False,
                'error': "Calibration point not specified"
            }), 400
        
        # Perform calibration
        calibrate_ph(point, value)
        
        return jsonify({
            'success': True,
            'message': f"pH sensor calibrated at {point} point"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/calibration/ec', methods=['POST'])
def calibrate_ec_endpoint():
    """Calibrate the EC sensor"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        point = data.get('point')
        value = data.get('value')
        
        if not point:
            return jsonify({
                'success': False,
                'error': "Calibration point not specified"
            }), 400
        
        # Perform calibration
        calibrate_ec(point, value)
        
        return jsonify({
            'success': True,
            'message': f"EC sensor calibrated at {point} point"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/calibration/temperature', methods=['POST'])
def calibrate_temp_endpoint():
    """Calibrate the temperature sensor"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        value = data.get('value')
        
        if value is None:
            return jsonify({
                'success': False,
                'error': "Calibration value not specified"
            }), 400
        
        # Perform calibration
        calibrate_temperature(value)
        
        return jsonify({
            'success': True,
            'message': f"Temperature sensor calibrated to {value}°C"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/export/readings', methods=['GET'])
def export_readings():
    """Export sensor readings as CSV or JSON"""
    try:
        # Get parameters
        format_type = request.args.get('format', 'json').lower()
        sensor_type = request.args.get('sensor', 'all').lower()
        limit = request.args.get('limit', 1000, type=int)
        
        # Get data
        if sensor_type == 'all':
            ph_readings = SensorReading.get_history('ph', limit)
            ec_readings = SensorReading.get_history('ec', limit)
            temp_readings = SensorReading.get_history('temp', limit)
            
            data = {
                'ph': [reading.to_dict() for reading in ph_readings],
                'ec': [reading.to_dict() for reading in ec_readings],
                'temp': [reading.to_dict() for reading in temp_readings]
            }
        else:
            readings = SensorReading.get_history(sensor_type, limit)
            data = [reading.to_dict() for reading in readings]
        
        # Return data in the requested format
        if format_type == 'csv':
            from flask import Response
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['sensor_type', 'value', 'timestamp'])
            
            # Write data
            if sensor_type == 'all':
                for sensor_name, readings in data.items():
                    for reading in readings:
                        writer.writerow([
                            sensor_name,
                            reading['value'],
                            reading['timestamp']
                        ])
            else:
                for reading in data:
                    writer.writerow([
                        reading['sensor_type'],
                        reading['value'],
                        reading['timestamp']
                    ])
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename=sensor_readings.csv'}
            )
        else:
            # Return JSON
            return jsonify({
                'success': True,
                'data': data
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sensor-current', methods=['GET'])
def get_current_sensor_values():
    """
    Return current sensor readings
    """
    try:
        # Get the latest sensor readings
        sensor_data = SensorData.get_latest()
        
        # If no sensor data yet, generate placeholder data
        if not sensor_data:
            return jsonify({
                'ph': 6.0,
                'ec': 1200,
                'temp': 22.5,
                'updated': datetime.now().isoformat(),
                'status': 'simulated'
            })
        
        # Format the response
        return jsonify({
            'ph': sensor_data.ph,
            'ec': sensor_data.ec,
            'temp': sensor_data.temperature,
            'updated': sensor_data.timestamp.isoformat(),
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/sensor-history', methods=['GET'])
def get_sensor_history_range():
    """
    Return sensor history for specified timeframe
    Timeframes: 1h, 6h, 24h, 7d
    """
    timeframe = request.args.get('timeframe', '24h')
    
    # Convert timeframe to timedelta
    if timeframe == '1h':
        time_delta = timedelta(hours=1)
    elif timeframe == '6h':
        time_delta = timedelta(hours=6)
    elif timeframe == '24h':
        time_delta = timedelta(hours=24)
    elif timeframe == '7d':
        time_delta = timedelta(days=7)
    else:
        time_delta = timedelta(hours=24)
    
    try:
        # Get sensor data from database
        start_time = datetime.now() - time_delta
        sensor_data = SensorData.get_range(start_time, datetime.now())
        
        # If no data available, return empty chart data with disconnected status
        if not sensor_data:
            return jsonify({
                'ph': {
                    'values': [],
                    'timestamps': [],
                    'status': 'disconnected'
                },
                'ec': {
                    'values': [],
                    'timestamps': [],
                    'status': 'disconnected'
                },
                'temp': {
                    'values': [],
                    'timestamps': [],
                    'status': 'disconnected'
                },
                'status': 'error',
                'message': 'No sensor data available'
            })
        
        # Format the data for charts
        timestamps = [reading.timestamp.isoformat() for reading in sensor_data]
        ph_values = [reading.ph for reading in sensor_data]
        ec_values = [reading.ec for reading in sensor_data]
        temp_values = [reading.temperature for reading in sensor_data]
        
        # Determine sensor status
        has_ph = any(v is not None for v in ph_values)
        has_ec = any(v is not None for v in ec_values)
        has_temp = any(v is not None for v in temp_values)
        
        return jsonify({
            'ph': {
                'values': ph_values,
                'timestamps': timestamps,
                'status': 'connected' if has_ph else 'disconnected'
            },
            'ec': {
                'values': ec_values,
                'timestamps': timestamps,
                'status': 'connected' if has_ec else 'disconnected'
            },
            'temp': {
                'values': temp_values,
                'timestamps': timestamps,
                'status': 'connected' if has_temp else 'disconnected'
            },
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """
    Return recent notifications
    """
    try:
        count = int(request.args.get('count', 5))
        notifications = Notification.get_recent(count)
        
        result = []
        for notification in notifications:
            result.append({
                'id': notification.id,
                'message': notification.message,
                'type': notification.type,
                'timestamp': notification.timestamp.isoformat(),
                'is_read': notification.is_read
            })
        
        return jsonify({
            'notifications': result,
            'count': len(result),
            'unread_count': sum(1 for n in result if not n['is_read']),
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    """
    Mark notifications as read
    """
    try:
        data = request.get_json()
        notification_ids = data.get('ids', [])
        
        if not notification_ids:
            # Mark all as read if no specific IDs provided
            Notification.mark_all_read()
        else:
            for nid in notification_ids:
                Notification.mark_read(nid)
        
        return jsonify({
            'status': 'ok',
            'message': 'Notifications marked as read'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/dose', methods=['POST'])
def manual_dose():
    """
    Trigger manual dosing
    """
    try:
        data = request.get_json()
        pump_id = data.get('pump_id')
        amount_ml = data.get('amount_ml')
        
        if not pump_id or not amount_ml:
            return jsonify({
                'status': 'error',
                'message': 'Missing pump_id or amount_ml'
            }), 400
        
        # Get the pump
        pump = Pump.get_by_id(pump_id)
        if not pump:
            return jsonify({
                'status': 'error',
                'message': f'Pump with ID {pump_id} not found'
            }), 404
        
        # Check if pump is enabled
        if not pump.is_enabled:
            return jsonify({
                'status': 'error',
                'message': f'Pump {pump.name} is disabled'
            }), 400
        
        # Perform the dosing
        seconds = pump.dose(amount_ml)
        
        # Create a notification
        Notification.create(
            message=f'Manual dose: {amount_ml}ml using {pump.name}',
            type='dosing'
        )
        
        return jsonify({
            'status': 'ok',
            'message': f'Dosed {amount_ml}ml using {pump.name}',
            'seconds_active': seconds
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/system-stats', methods=['GET'])
def get_system_stats():
    """
    Return system statistics (CPU, memory, disk)
    """
    try:
        # This is simplified - in a real app we'd use psutil
        # or similar to get actual system stats
        return jsonify({
            'cpu_usage': random.randint(5, 30),
            'memory_usage': random.randint(20, 60),
            'disk_usage': random.randint(10, 90),
            'uptime': str(timedelta(hours=random.randint(1, 1000))),
            'temperature': round(random.uniform(40, 60), 1),
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/test-notification', methods=['POST'])
def test_notification():
    """Send a test notification"""
    try:
        data = request.get_json()
        notification_type = data.get('type', 'all')
        destination = data.get('destination', '')
        
        # Import notification utilities
        from app.utils.notification_manager import send_email, send_sms
        
        if notification_type == 'email':
            # Test email notification
            if not destination:
                return jsonify({
                    'success': False,
                    'error': 'Email address is required'
                }), 400
            
            send_email(
                to=destination,
                subject="Test Email from NuTetra Controller",
                body="This is a test email from your NuTetra Controller system."
            )
            return jsonify({
                'success': True,
                'message': f'Test email sent to {destination}'
            })
            
        elif notification_type == 'sms':
            # Test SMS notification
            if not destination:
                return jsonify({
                    'success': False,
                    'error': 'Phone number is required'
                }), 400
                
            send_sms(
                to=destination,
                message="Test SMS from NuTetra Controller: This is a test message."
            )
            return jsonify({
                'success': True,
                'message': f'Test SMS sent to {destination}'
            })
            
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown notification type: {notification_type}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-brands', methods=['GET'])
def get_nutrient_brands():
    """Get all nutrient brands"""
    try:
        brands = NutrientBrand.query.all()
        
        return jsonify({
            'success': True,
            'data': [brand.to_dict() for brand in brands]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-brands/<int:brand_id>/products', methods=['GET'])
def get_brand_products(brand_id):
    """Get all products for a specific nutrient brand"""
    try:
        brand = NutrientBrand.query.get(brand_id)
        if not brand:
            return jsonify({
                'success': False,
                'error': f"Brand with ID {brand_id} not found"
            }), 404
        
        products = NutrientProduct.query.filter_by(brand_id=brand_id).all()
        
        return jsonify({
            'success': True,
            'data': [product.to_dict() for product in products]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-brands', methods=['POST'])
def create_nutrient_brand():
    """Create a new nutrient brand"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({
                'success': False,
                'error': "Missing required field: name"
            }), 400
        
        # Check if brand already exists
        existing_brand = NutrientBrand.query.filter_by(name=data['name']).first()
        if existing_brand:
            return jsonify({
                'success': False,
                'error': f"Brand '{data['name']}' already exists"
            }), 400
        
        # Create new brand
        new_brand = NutrientBrand(
            name=data['name'],
            description=data.get('description')
        )
        
        # Save to database
        db.session.add(new_brand)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Nutrient brand created successfully",
            'data': new_brand.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-products', methods=['POST'])
def create_nutrient_product():
    """Create a new nutrient product"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['brand_id', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        # Check if brand exists
        brand = NutrientBrand.query.get(data['brand_id'])
        if not brand:
            return jsonify({
                'success': False,
                'error': f"Brand with ID {data['brand_id']} not found"
            }), 404
        
        # Validate nutrient_type if provided
        valid_types = ['grow', 'bloom', 'micro', 'calmag', 'other']
        nutrient_type = data.get('nutrient_type')
        if nutrient_type and nutrient_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f"Invalid nutrient type: {nutrient_type}. Must be one of: {', '.join(valid_types)}"
            }), 400
        
        # Create new product
        new_product = NutrientProduct(
            brand_id=data['brand_id'],
            name=data['name'],
            description=data.get('description'),
            nitrogen_pct=data.get('nitrogen_pct'),
            phosphorus_pct=data.get('phosphorus_pct'),
            potassium_pct=data.get('potassium_pct'),
            nutrient_type=nutrient_type
        )
        
        # Save to database
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Nutrient product created successfully",
            'data': new_product.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-products/<int:product_id>', methods=['PUT'])
def update_nutrient_product(product_id):
    """Update an existing nutrient product"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400
        
        # Find the product
        product = NutrientProduct.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': f"Product with ID {product_id} not found"
            }), 404
        
        # Validate nutrient_type if provided
        valid_types = ['grow', 'bloom', 'micro', 'calmag', 'other']
        nutrient_type = data.get('nutrient_type')
        if nutrient_type and nutrient_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f"Invalid nutrient type: {nutrient_type}. Must be one of: {', '.join(valid_types)}"
            }), 400
        
        # Update fields
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'nitrogen_pct' in data:
            product.nitrogen_pct = data['nitrogen_pct']
        if 'phosphorus_pct' in data:
            product.phosphorus_pct = data['phosphorus_pct']
        if 'potassium_pct' in data:
            product.potassium_pct = data['potassium_pct']
        if nutrient_type:
            product.nutrient_type = nutrient_type
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Nutrient product updated successfully",
            'data': product.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-products/<int:product_id>', methods=['DELETE'])
def delete_nutrient_product(product_id):
    """Delete a nutrient product"""
    try:
        # Find the product
        product = NutrientProduct.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': f"Product with ID {product_id} not found"
            }), 404
        
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        
        # Reconfigure nutrient components in plant profiles
        Settings.auto_configure_nutrient_components()
        
        return jsonify({
            'success': True,
            'message': f"Product '{product.name}' deleted successfully"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/nutrient-brands/initialize', methods=['POST'])
def initialize_nutrient_brands():
    """Initialize default nutrient brands and products if none exist"""
    try:
        from app.models.nutrient import NutrientBrand
        
        # Check if brands already exist
        existing_count = NutrientBrand.query.count()
        
        if existing_count > 0:
            return jsonify({
                'success': True,
                'message': f"{existing_count} nutrient brands already exist",
                'initialized': False
            })
        
        # Initialize defaults
        NutrientBrand.initialize_defaults()
        
        # Count how many were created
        new_count = NutrientBrand.query.count()
        
        return jsonify({
            'success': True,
            'message': f"Successfully initialized {new_count} nutrient brands",
            'initialized': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/pumps/migrate-types', methods=['POST'])
def migrate_pump_types():
    """Migrate old nutrient_a, nutrient_b, etc. types to the generic 'nutrient' type"""
    try:
        # Find all pumps with old nutrient types
        old_pumps = Pump.query.filter(
            Pump.type.like('nutrient_%')
        ).all()
        
        count = 0
        for pump in old_pumps:
            # Skip ph pumps which also start with nutrient_
            if pump.type in ['ph_up', 'ph_down']:
                continue
                
            # Update the type to the generic 'nutrient'
            pump.type = 'nutrient'
            count += 1
        
        # Commit the changes
        if count > 0:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'message': f"Successfully migrated {count} pumps to generic nutrient type",
            'count': count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 