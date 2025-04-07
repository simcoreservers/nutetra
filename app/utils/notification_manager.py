import logging
import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.settings import Settings

# Create a logger for this module
logger = logging.getLogger(__name__)

def send_notification(subject, message, level='info'):
    """Send a notification through all enabled channels"""
    # Skip if notifications are disabled
    if not Settings.get('notifications_enabled', True):
        return False
    
    # Log the notification
    if level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)
    else:
        logger.info(message)
    
    success = False
    
    # Send email notification if enabled
    if Settings.get('email_notifications', False):
        email_success = send_email(subject, message)
        success = success or email_success
    
    # Send SMS notification if enabled
    if Settings.get('sms_notifications', False):
        sms_success = send_sms(message)
        success = success or sms_success
    
    # Always emit the notification through SocketIO
    try:
        from app import socketio
        socketio.emit('notification', {
            'subject': subject,
            'message': message,
            'level': level
        })
        success = True
    except Exception as e:
        logger.error(f"Error sending SocketIO notification: {e}")
    
    return success

def send_email(subject, body):
    """Send an email notification"""
    try:
        # Get email settings
        email_address = Settings.get('email_address', '')
        email_password = Settings.get('email_password', '')
        email_smtp_server = Settings.get('email_smtp_server', 'smtp.gmail.com')
        email_smtp_port = Settings.get('email_smtp_port', 587)
        
        if not email_address or not email_password:
            logger.warning("Email notifications enabled but not configured properly")
            return False
        
        # Set up the email message
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = email_address  # Sending to self
        msg['Subject'] = f"NuTetra Alert: {subject}"
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server and send
        server = smtplib.SMTP(email_smtp_server, email_smtp_port)
        server.starttls()
        server.login(email_address, email_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email notification sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False

def send_sms(message):
    """Send an SMS notification"""
    try:
        # Get SMS settings
        phone_number = Settings.get('phone_number', '')
        sms_api_key = Settings.get('sms_api_key', '')
        sms_service = Settings.get('sms_service', 'twilio')
        
        if not phone_number or not sms_api_key:
            logger.warning("SMS notifications enabled but not configured properly")
            return False
        
        if sms_service == 'twilio':
            return send_twilio_sms(message, phone_number)
        else:
            logger.warning(f"Unsupported SMS service: {sms_service}")
            return False
    except Exception as e:
        logger.error(f"Failed to send SMS notification: {e}")
        return False

def send_twilio_sms(message, phone_number):
    """Send an SMS via Twilio"""
    try:
        account_sid = Settings.get('twilio_account_sid', '')
        auth_token = Settings.get('twilio_auth_token', '')
        twilio_number = Settings.get('twilio_phone_number', '')
        
        if not account_sid or not auth_token or not twilio_number:
            logger.warning("Twilio SMS not configured properly")
            return False
        
        # Format the phone number if needed
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # Twilio API URL
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        # Prepare the request
        payload = {
            'From': twilio_number,
            'To': phone_number,
            'Body': f"NuTetra Alert: {message}"
        }
        
        # Send the request
        response = requests.post(
            url, 
            data=payload, 
            auth=(account_sid, auth_token)
        )
        
        # Check if successful
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("SMS notification sent successfully")
            return True
        else:
            logger.error(f"Failed to send SMS: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Twilio SMS: {e}")
        return False

def notify_out_of_range(sensor_type, value, min_value, max_value):
    """Send a notification when a sensor reading is out of range"""
    if sensor_type == 'ph':
        subject = "pH Level Alert"
        message = f"pH level is out of range: {value:.2f} (target: {min_value:.2f}-{max_value:.2f})"
    elif sensor_type == 'ec':
        subject = "EC Level Alert"
        message = f"EC level is out of range: {value:.2f} (target: {min_value:.2f}-{max_value:.2f})"
    elif sensor_type == 'temp':
        subject = "Temperature Alert"
        message = f"Temperature is out of range: {value:.1f}°C (target: {min_value:.1f}-{max_value:.1f}°C)"
    else:
        subject = "Sensor Alert"
        message = f"{sensor_type} reading is out of range: {value} (target: {min_value}-{max_value})"
    
    level = 'warning'
    return send_notification(subject, message, level) 