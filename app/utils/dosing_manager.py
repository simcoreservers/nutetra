import time
import threading
import logging
import lgpio
from app import scheduler
from app.models.pump import Pump
from app.models.dosing_event import DosingEvent
from app.models.settings import Settings
from app.utils.sensor_manager import get_last_reading, read_sensor
from datetime import datetime, time as dt_time

# Create a logger for this module
logger = logging.getLogger(__name__)

# Time of last dosing for each type
last_dosing = {
    'ph_up': 0,
    'ph_down': 0,
    'nutrient_a': 0,
    'nutrient_b': 0,
    'nutrient_c': 0
}

# Lock for thread safety when controlling pumps
pump_lock = threading.Lock()

# lgpio chip handle
chip = None

def init_dosing():
    """Initialize the dosing system and GPIO pins"""
    global chip
    try:
        # Set up lgpio
        chip = lgpio.gpiochip_open(0)  # Open the default gpiochip
        
        # Set up pins for all pumps
        pumps = Pump.get_enabled()
        for pump in pumps:
            lgpio.gpio_claim_output(chip, pump.gpio_pin)
            lgpio.gpio_write(chip, pump.gpio_pin, 0)  # Ensure all pumps are off (0 = LOW)
        
        logger.info(f"Initialized {len(pumps)} dosing pumps")
        
        # Initialize default pumps if needed
        Pump.initialize_defaults()
        
        # Schedule dosing checks
        schedule_dosing_checks()
        
    except Exception as e:
        logger.error(f"Failed to initialize dosing system: {e}")

def schedule_dosing_checks():
    """Schedule regular checks for pH and EC levels"""
    # Only schedule if auto-dosing is enabled
    if not Settings.get('auto_dosing_enabled', True):
        logger.info("Auto-dosing is disabled, not scheduling dosing checks")
        return
    
    # Schedule pH check
    ph_interval = Settings.get('ph_check_interval', 300)
    scheduler.add_job(
        check_and_adjust_ph,
        'interval',
        seconds=ph_interval,
        id='ph_check',
        replace_existing=True
    )
    
    # Schedule EC check
    ec_interval = Settings.get('ec_check_interval', 300)
    scheduler.add_job(
        check_and_adjust_ec,
        'interval',
        seconds=ec_interval,
        id='ec_check',
        replace_existing=True
    )
    
    logger.info("Dosing check schedules initialized")

def check_night_mode():
    """Check if night mode is active based on current time"""
    night_mode_enabled = Settings.get('night_mode_enabled', False)
    if not night_mode_enabled:
        return False
    
    # Get night mode start and end times
    start_str = Settings.get('night_mode_start', '22:00')
    end_str = Settings.get('night_mode_end', '06:00')
    
    # Parse the time strings
    try:
        start_time = dt_time(
            *map(int, start_str.split(':'))
        )
        end_time = dt_time(
            *map(int, end_str.split(':'))
        )
        
        # Get current time
        now = datetime.now().time()
        
        # Check if current time is within night mode
        if start_time > end_time:  # Crosses midnight
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time
    except Exception as e:
        logger.error(f"Error checking night mode: {e}")
        return False

def activate_pump(pump_id, duration_ms, reason=None, sensor_before=None):
    """Activate a pump for the specified duration in milliseconds"""
    global chip
    with pump_lock:  # Ensure thread safety
        try:
            # Get the pump from database
            pump = Pump.query.get(pump_id)
            if not pump or not pump.enabled:
                logger.warning(f"Cannot activate pump {pump_id}: not found or disabled")
                return False
            
            # Check if in night mode
            if check_night_mode():
                logger.info(f"Dosing skipped for pump {pump.name}: night mode active")
                return False
            
            # Check if we've dosed recently with this pump type
            current_time = time.time()
            wait_time = Settings.get(f"{pump.type}_dose_wait_time", 60)
            
            if current_time - last_dosing.get(pump.type, 0) < wait_time:
                logger.info(f"Dosing skipped for pump {pump.name}: waiting period not elapsed")
                return False
            
            # Calculate the amount being dosed
            amount_ml = (duration_ms / 1000.0) * pump.flow_rate
            
            # Record the time of this dosing
            last_dosing[pump.type] = current_time
            
            # If no sensor reading provided, get it now
            sensor_value = sensor_before
            if sensor_value is None and pump.type.startswith('ph'):
                sensor_value = get_last_reading('ph')
            elif sensor_value is None and pump.type.startswith('nutrient'):
                sensor_value = get_last_reading('ec')
            
            # Set the GPIO pin HIGH to activate the pump (1 = HIGH)
            lgpio.gpio_write(chip, pump.gpio_pin, 1)
            logger.info(f"Activated pump {pump.name} for {duration_ms}ms ({amount_ml:.2f}ml)")
            
            # Wait for the specified duration
            time.sleep(duration_ms / 1000.0)
            
            # Set the GPIO pin LOW to deactivate the pump (0 = LOW)
            lgpio.gpio_write(chip, pump.gpio_pin, 0)
            
            # Read the sensor again after dosing
            sensor_after = None
            # Allow time for the solution to mix
            if pump.type.startswith('ph'):
                # Wait a few seconds before reading the pH again
                time.sleep(5)
                try:
                    sensor_after = read_sensor('ph')
                except Exception as e:
                    logger.error(f"Error reading pH after dosing: {e}")
            elif pump.type.startswith('nutrient'):
                # Wait a few seconds before reading the EC again
                time.sleep(5)
                try:
                    sensor_after = read_sensor('ec')
                except Exception as e:
                    logger.error(f"Error reading EC after dosing: {e}")
            
            # Log the dosing event
            DosingEvent.log_event(
                pump_id=pump_id,
                amount_ml=amount_ml,
                duration_ms=duration_ms,
                reason=reason or 'manual',
                sensor_before=sensor_value,
                sensor_after=sensor_after
            )
            
            # Emit the dosing event through SocketIO for real-time updates
            from app import socketio
            socketio.emit('dosing_event', {
                'pump_id': pump_id,
                'pump_name': pump.name,
                'amount_ml': amount_ml,
                'duration_ms': duration_ms,
                'reason': reason or 'manual',
                'timestamp': time.time()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error activating pump {pump_id}: {e}")
            # Make sure the pump is off in case of error
            try:
                if 'pump' in locals() and pump and chip is not None:
                    lgpio.gpio_write(chip, pump.gpio_pin, 0)
            except:
                pass
            return False

def calculate_dose_amount(pump_type):
    """Calculate the dose amount for a specific pump type based on settings"""
    if pump_type.startswith('ph'):
        return Settings.get('ph_dose_amount', 1.0)
    elif pump_type.startswith('nutrient'):
        return Settings.get('ec_dose_amount', 5.0)
    return 1.0  # Default

def check_and_adjust_ph():
    """Check pH level and dose if needed"""
    # We need to use Flask's app context for database operations
    from flask import current_app
    
    with current_app.app_context():
        # Skip if auto-dosing is disabled
        if not Settings.get('auto_dosing_enabled', True):
            return
        
        try:
            # Get current pH
            current_ph = get_last_reading('ph')
            if current_ph is None:
                logger.warning("Cannot adjust pH: no pH reading available")
                return
            
            # Get target pH range
            target_min = Settings.get('ph_target_min', 5.8)
            target_max = Settings.get('ph_target_max', 6.2)
            
            # Check if pH is out of range
            if current_ph < target_min:
                # pH is too low, need to add pH Up
                logger.info(f"pH is low ({current_ph}), adding pH Up")
                
                # Get pH Up pumps
                ph_up_pumps = Pump.get_by_type('ph_up')
                if not ph_up_pumps:
                    logger.warning("Cannot adjust pH: no pH Up pumps configured")
                    return
                
                # Use the first available pH Up pump
                pump = ph_up_pumps[0]
                
                # Calculate dose amount and duration
                amount_ml = calculate_dose_amount('ph_up')
                duration_ms = pump.calculate_dosing_time(amount_ml)
                
                # Activate the pump
                activate_pump(
                    pump_id=pump.id,
                    duration_ms=duration_ms,
                    reason='ph_low',
                    sensor_before=current_ph
                )
                
            elif current_ph > target_max:
                # pH is too high, need to add pH Down
                logger.info(f"pH is high ({current_ph}), adding pH Down")
                
                # Get pH Down pumps
                ph_down_pumps = Pump.get_by_type('ph_down')
                if not ph_down_pumps:
                    logger.warning("Cannot adjust pH: no pH Down pumps configured")
                    return
                
                # Use the first available pH Down pump
                pump = ph_down_pumps[0]
                
                # Calculate dose amount and duration
                amount_ml = calculate_dose_amount('ph_down')
                duration_ms = pump.calculate_dosing_time(amount_ml)
                
                # Activate the pump
                activate_pump(
                    pump_id=pump.id,
                    duration_ms=duration_ms,
                    reason='ph_high',
                    sensor_before=current_ph
                )
            else:
                logger.debug(f"pH is within range ({current_ph}), no adjustment needed")
                
        except Exception as e:
            logger.error(f"Error in pH adjustment: {e}")

def check_and_adjust_ec():
    """Check EC level and dose if needed"""
    # We need to use Flask's app context for database operations
    from flask import current_app
    
    with current_app.app_context():
        # Skip if auto-dosing is disabled
        if not Settings.get('auto_dosing_enabled', True):
            return
        
        try:
            # Get current EC
            current_ec = get_last_reading('ec')
            if current_ec is None:
                logger.warning("Cannot adjust EC: no EC reading available")
                return
            
            # Get target EC range
            target_min = Settings.get('ec_target_min', 1.2)
            target_max = Settings.get('ec_target_max', 1.5)
            
            # Check if EC is too low (we can only add nutrients, not remove them)
            if current_ec < target_min:
                logger.info(f"EC is low ({current_ec}), adding nutrients")
                
                # Add nutrients in sequence (A, B, C)
                for nutrient_type in ['nutrient_a', 'nutrient_b', 'nutrient_c']:
                    pumps = Pump.get_by_type(nutrient_type)
                    if not pumps:
                        logger.debug(f"No {nutrient_type} pumps configured")
                        continue
                    
                    # Use the first available pump of this type
                    pump = pumps[0]
                    
                    # Calculate dose amount and duration
                    amount_ml = calculate_dose_amount(nutrient_type)
                    duration_ms = pump.calculate_dosing_time(amount_ml)
                    
                    # Activate the pump
                    activate_pump(
                        pump_id=pump.id,
                        duration_ms=duration_ms,
                        reason='ec_low',
                        sensor_before=current_ec
                    )
                    
                    # Wait between nutrient additions to prevent precipitation
                    time.sleep(5)
            else:
                logger.debug(f"EC is within range ({current_ec}), no adjustment needed")
                
        except Exception as e:
            logger.error(f"Error in EC adjustment: {e}")

def cleanup():
    """Clean up GPIO resources"""
    global chip
    if chip is not None:
        try:
            lgpio.gpiochip_close(chip)
        except Exception as e:
            logger.error(f"Error closing GPIO chip: {e}") 