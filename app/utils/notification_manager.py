import logging
import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.settings import Settings

# Configure logging
logger = logging.getLogger('app.notifications')

def notify_out_of_range(sensor_type, current_value, min_value, max_value):
    """
    Send a notification when a sensor reading is out of range
    
    Args:
        sensor_type: Type of sensor (ph, ec, temp)
        current_value: Current sensor reading
        min_value: Minimum acceptable value
        max_value: Maximum acceptable value
    """
    # Check if notifications are enabled
    if not Settings.get('notifications_enabled', True):
        return False
    
    # Check if this specific notification is enabled
    setting_key = f'notify_{sensor_type.lower()}'
    if not Settings.get(setting_key, True):
        return False
    
    # Determine the notification level
    if sensor_type == 'ph':
        formatted_value = f"{current_value:.2f}"
        formatted_min = f"{min_value:.2f}"
        formatted_max = f"{max_value:.2f}"
        unit = ""
    elif sensor_type == 'ec':
        formatted_value = f"{current_value}"
        formatted_min = f"{min_value}"
        formatted_max = f"{max_value}"
        unit = "μS/cm"
    elif sensor_type == 'temp':
        formatted_value = f"{current_value:.1f}"
        formatted_min = f"{min_value:.1f}"
        formatted_max = f"{max_value:.1f}"
        unit = "°C"
    else:
        formatted_value = str(current_value)
        formatted_min = str(min_value)
        formatted_max = str(max_value)
        unit = ""
    
    # Create notification message
    subject = f"Alert: {sensor_type.upper()} out of range"
    message = f"Your {sensor_type.upper()} reading is out of range.\n\n"
    message += f"Current value: {formatted_value}{unit}\n"
    message += f"Acceptable range: {formatted_min}{unit} - {formatted_max}{unit}"
    
    # Send the notification
    return send_notification(subject, message, "warning")

def send_notification(subject, message, level="info"):
    """
    Send a notification through configured channels
    
    Args:
        subject: Notification subject
        message: Notification message
        level: Notification level (info, warning, critical)
    
    Returns:
        Boolean indicating if any notification was sent
    """
    # Check notification level filter
    notification_level = Settings.get('notification_level', 'info')
    
    if notification_level == 'critical' and level != 'critical':
        return False
    if notification_level == 'warning' and level not in ['warning', 'critical']:
        return False
    
    # Track if any notification is sent
    notifications_sent = False
    
    # Send email notification
    if Settings.get('email_notifications', False):
        try:
            email_address = Settings.get('email_address', '')
            if email_address:
                sent = send_email(email_address, subject, message)
                notifications_sent = notifications_sent or sent
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    # Send SMS notification
    if Settings.get('sms_notifications', False):
        try:
            phone_number = Settings.get('phone_number', '')
            if phone_number:
                # For SMS, only send if level matches frequency, or it's critical
                sms_frequency = Settings.get('sms_frequency', 'critical')
                if level == 'critical' or sms_frequency == 'all':
                    sent = send_sms(phone_number, f"{subject}: {message}")
                    notifications_sent = notifications_sent or sent
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
    
    return notifications_sent

def send_email(to, subject, body):
    """
    Send an email notification
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
    
    Returns:
        Boolean indicating if email was sent
    """
    # Get email settings
    smtp_server = Settings.get('smtp_server', 'smtp.gmail.com')
    smtp_port = Settings.get('smtp_port', 587)
    email_user = Settings.get('email_user', '')
    email_password = Settings.get('email_password', '')
    from_name = Settings.get('system_name', 'NuTetra Controller')
    
    # Validate settings
    if not email_user or not email_password:
        logger.error("Email settings not configured")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{email_user}>"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
        
        logger.info(f"Email notification sent to {to}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_sms(to, message):
    """
    Send an SMS notification
    
    Args:
        to: Recipient phone number
        message: SMS message
    
    Returns:
        Boolean indicating if SMS was sent
    """
    # Get SMS settings
    sms_service = Settings.get('sms_service', 'twilio')
    
    if sms_service == 'twilio':
        return send_sms_twilio(to, message)
    else:
        logger.error(f"Unsupported SMS service: {sms_service}")
        return False

def send_sms_twilio(to, message):
    """
    Send an SMS using Twilio
    
    Args:
        to: Recipient phone number
        message: SMS message
    
    Returns:
        Boolean indicating if SMS was sent
    """
    # Get Twilio settings
    account_sid = Settings.get('twilio_account_sid', '')
    auth_token = Settings.get('twilio_auth_token', '')
    from_number = Settings.get('twilio_phone_number', '')
    
    # Validate settings
    if not account_sid or not auth_token or not from_number:
        logger.error("Twilio settings not configured")
        return False
    
    try:
        # Import Twilio client here to avoid dependency for those who don't use it
        from twilio.rest import Client
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Send message
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=to
        )
        
        logger.info(f"SMS notification sent to {to} (SID: {message.sid})")
        return True
    
    except ImportError:
        logger.error("Twilio package not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False 