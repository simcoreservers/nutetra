from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.settings import Settings
from app.models.pump import Pump
from app.models.dosing_event import DosingEvent
from app.utils.notification_manager import send_notification
from app import db
import os
import json
import platform
import socket
import subprocess
import re
import netifaces
import psutil

# Create a blueprint
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
def index():
    """Show main settings page"""
    return render_template('settings/index.html')

@settings_bp.route('/system', methods=['GET', 'POST'])
def system():
    """Manage system settings"""
    if request.method == 'POST':
        # Get values from form
        dark_mode = 'dark_mode' in request.form
        refresh_interval = request.form.get('refresh_interval', type=int)
        chart_points = request.form.get('chart_points', type=int)
        logging_interval = request.form.get('logging_interval', type=int)
        
        # Update settings
        Settings.set('dark_mode', dark_mode)
        
        if refresh_interval is not None:
            Settings.set('refresh_interval', refresh_interval)
        
        if chart_points is not None:
            Settings.set('chart_points', chart_points)
        
        if logging_interval is not None:
            Settings.set('logging_interval', logging_interval)
        
        flash('System settings updated successfully', 'success')
        return redirect(url_for('settings.system'))
    
    # Get current settings for display
    settings = {
        'dark_mode': Settings.get('dark_mode', True),
        'refresh_interval': Settings.get('refresh_interval', 10),
        'chart_points': Settings.get('chart_points', 50),
        'logging_interval': Settings.get('logging_interval', 300)
    }
    
    return render_template(
        'settings/system.html',
        settings=settings
    )

@settings_bp.route('/notifications', methods=['GET', 'POST'])
def notifications():
    """Manage notification settings"""
    if request.method == 'POST':
        # Get values from form
        notifications_enabled = 'notifications_enabled' in request.form
        email_notifications = 'email_notifications' in request.form
        sms_notifications = 'sms_notifications' in request.form
        
        email_address = request.form.get('email_address')
        email_password = request.form.get('email_password')
        email_smtp_server = request.form.get('email_smtp_server')
        email_smtp_port = request.form.get('email_smtp_port', type=int)
        
        phone_number = request.form.get('phone_number')
        sms_service = request.form.get('sms_service')
        sms_api_key = request.form.get('sms_api_key')
        
        # Additional Twilio settings
        twilio_account_sid = request.form.get('twilio_account_sid')
        twilio_auth_token = request.form.get('twilio_auth_token')
        twilio_phone_number = request.form.get('twilio_phone_number')
        
        # Update basic settings
        Settings.set('notifications_enabled', notifications_enabled)
        Settings.set('email_notifications', email_notifications)
        Settings.set('sms_notifications', sms_notifications)
        
        # Update email settings if provided
        if email_address:
            Settings.set('email_address', email_address)
        
        # Only update password if provided (don't overwrite with empty)
        if email_password:
            Settings.set('email_password', email_password)
        
        if email_smtp_server:
            Settings.set('email_smtp_server', email_smtp_server)
        
        if email_smtp_port:
            Settings.set('email_smtp_port', email_smtp_port)
        
        # Update SMS settings if provided
        if phone_number:
            Settings.set('phone_number', phone_number)
        
        if sms_service:
            Settings.set('sms_service', sms_service)
        
        if sms_api_key:
            Settings.set('sms_api_key', sms_api_key)
        
        # Update Twilio settings if provided
        if twilio_account_sid:
            Settings.set('twilio_account_sid', twilio_account_sid)
        
        if twilio_auth_token:
            Settings.set('twilio_auth_token', twilio_auth_token)
        
        if twilio_phone_number:
            Settings.set('twilio_phone_number', twilio_phone_number)
        
        flash('Notification settings updated successfully', 'success')
        return redirect(url_for('settings.notifications'))
    
    # Get current settings for display
    settings = {
        'notifications_enabled': Settings.get('notifications_enabled', True),
        'email_notifications': Settings.get('email_notifications', False),
        'email_address': Settings.get('email_address', ''),
        'email_smtp_server': Settings.get('email_smtp_server', 'smtp.gmail.com'),
        'email_smtp_port': Settings.get('email_smtp_port', 587),
        'sms_notifications': Settings.get('sms_notifications', False),
        'phone_number': Settings.get('phone_number', ''),
        'sms_service': Settings.get('sms_service', 'twilio'),
        'twilio_account_sid': Settings.get('twilio_account_sid', ''),
        'twilio_phone_number': Settings.get('twilio_phone_number', '')
    }
    
    # Mask secrets (auth token, API key)
    sms_api_key = Settings.get('sms_api_key', '')
    settings['sms_api_key_set'] = bool(sms_api_key)
    
    twilio_auth_token = Settings.get('twilio_auth_token', '')
    settings['twilio_auth_token_set'] = bool(twilio_auth_token)
    
    email_password = Settings.get('email_password', '')
    settings['email_password_set'] = bool(email_password)
    
    return render_template(
        'settings/notifications.html',
        settings=settings
    )

@settings_bp.route('/test_notification', methods=['POST'])
def test_notification():
    """Send a test notification"""
    try:
        # Get notification type
        notification_type = request.form.get('type', 'all')
        
        if notification_type == 'email' or notification_type == 'all':
            # Test email notification
            if Settings.get('email_notifications', False):
                send_notification(
                    subject="Test Email Notification",
                    message="This is a test notification from your NuTetra Controller.",
                    level="info"
                )
        
        if notification_type == 'sms' or notification_type == 'all':
            # Test SMS notification
            if Settings.get('sms_notifications', False):
                send_notification(
                    subject="Test SMS",
                    message="This is a test SMS from your NuTetra Controller.",
                    level="info"
                )
        
        flash('Test notification sent successfully', 'success')
    except Exception as e:
        flash(f'Error sending test notification: {str(e)}', 'error')
    
    return redirect(url_for('settings.notifications'))

@settings_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    """Backup and restore system settings"""
    if request.method == 'POST':
        # Check if this is a restore operation
        if 'restore_file' in request.files:
            restore_file = request.files['restore_file']
            
            if restore_file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('settings.backup'))
            
            try:
                # Read and parse the backup file
                backup_data = json.loads(restore_file.read().decode('utf-8'))
                
                # Restore settings
                if 'settings' in backup_data:
                    for key, value in backup_data['settings'].items():
                        Settings.set(key, value)
                
                # Restore pumps
                if 'pumps' in backup_data:
                    # Clear existing pumps
                    Pump.query.delete()
                    
                    # Add pumps from backup
                    for pump_data in backup_data['pumps']:
                        pump = Pump(
                            name=pump_data['name'],
                            type=pump_data['type'],
                            gpio_pin=pump_data['gpio_pin'],
                            flow_rate=pump_data['flow_rate'],
                            enabled=pump_data.get('enabled', True)
                        )
                        db.session.add(pump)
                
                db.session.commit()
                flash('System restored successfully from backup', 'success')
            except Exception as e:
                flash(f'Error restoring from backup: {str(e)}', 'error')
            
            return redirect(url_for('settings.backup'))
    
    # Create backup data for download
    backup_data = {
        'settings': Settings.get_all(),
        'pumps': [pump.to_dict() for pump in Pump.query.all()]
    }
    
    # Generate a timestamp for the backup filename
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"nutetra_backup_{timestamp}.json"
    
    return render_template(
        'settings/backup.html',
        backup_data=json.dumps(backup_data, indent=2),
        backup_filename=backup_filename
    )

@settings_bp.route('/reset', methods=['POST'])
def reset():
    """Reset the system to default settings"""
    try:
        # Get the reset type
        reset_type = request.form.get('reset_type')
        
        if reset_type == 'settings':
            # Reset all settings to defaults
            Settings.query.delete()
            db.session.commit()
            
            # Re-initialize default settings
            Settings.initialize_defaults()
            
            flash('Settings reset to defaults successfully', 'success')
        
        elif reset_type == 'pumps':
            # Reset all pumps to defaults
            Pump.query.delete()
            db.session.commit()
            
            # Re-initialize default pumps
            Pump.initialize_defaults()
            
            flash('Pumps reset to defaults successfully', 'success')
        
        elif reset_type == 'all':
            # Reset everything
            from app.models.sensor_reading import SensorReading
            from app.models.dosing_event import DosingEvent
            from app.models.pump import Pump
            
            # Delete all data
            SensorReading.query.delete()
            DosingEvent.query.delete()
            Pump.query.delete()
            Settings.query.delete()
            db.session.commit()
            
            # Re-initialize defaults
            Settings.initialize_defaults()
            Pump.initialize_defaults()
            
            flash('System reset to defaults successfully', 'success')
        
        else:
            flash('Invalid reset type', 'error')
    
    except Exception as e:
        flash(f'Error resetting system: {str(e)}', 'error')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/diagnostics')
def diagnostics():
    """Show system diagnostics information"""
    # Collect system information
    import platform
    import psutil
    
    try:
        # System info
        system_info = {
            'os': platform.platform(),
            'python': platform.python_version(),
            'hostname': platform.node()
        }
        
        # Hardware info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        hardware_info = {
            'cpu_percent': cpu_percent,
            'memory_total': f"{memory.total / (1024**3):.2f} GB",
            'memory_used': f"{memory.used / (1024**3):.2f} GB",
            'memory_percent': memory_percent,
            'disk_total': f"{disk.total / (1024**3):.2f} GB",
            'disk_used': f"{disk.used / (1024**3):.2f} GB",
            'disk_percent': disk_percent
        }
        
        # I2C device scan (check sensor connectivity)
        import smbus2
        i2c_devices = []
        try:
            bus = smbus2.SMBus(1)
            for address in range(0x03, 0x78):
                try:
                    bus.read_byte(address)
                    i2c_devices.append(f"0x{address:02X}")
                except:
                    pass
        except:
            i2c_devices = ["I2C bus not accessible"]
        
        # Get sensor status
        from app.utils.sensor_manager import SENSOR_ADDRESSES
        sensor_status = {}
        for sensor_type, address in SENSOR_ADDRESSES.items():
            hex_address = f"0x{address:02X}"
            sensor_status[sensor_type] = {
                'address': hex_address,
                'connected': hex_address in i2c_devices,
                'last_reading': None
            }
            
            # Get last reading
            from app.models.sensor_reading import SensorReading
            last_reading = SensorReading.get_latest(sensor_type)
            if last_reading:
                sensor_status[sensor_type]['last_reading'] = {
                    'value': last_reading.value,
                    'timestamp': last_reading.timestamp.isoformat()
                }
        
        # Get database stats
        db_stats = {
            'sensor_readings': SensorReading.query.count(),
            'dosing_events': DosingEvent.query.count(),
            'settings': Settings.query.count(),
            'pumps': Pump.query.count()
        }
        
        return render_template(
            'settings/diagnostics.html',
            system_info=system_info,
            hardware_info=hardware_info,
            i2c_devices=i2c_devices,
            sensor_status=sensor_status,
            db_stats=db_stats
        )
    except Exception as e:
        error_message = str(e)
        return render_template(
            'settings/diagnostics.html',
            error=error_message
        )

@settings_bp.route('/network', methods=['GET', 'POST'])
def network():
    """Network configuration settings"""
    success_message = None
    error_message = None
    
    if request.method == 'POST':
        try:
            # Update hostname
            if 'update_hostname' in request.form:
                hostname = request.form.get('hostname')
                if hostname and re.match(r'^[a-zA-Z0-9-]+$', hostname):
                    # Save the hostname to settings
                    Settings.set('hostname', hostname)
                    
                    # Update the actual system hostname (requires sudo)
                    try:
                        subprocess.run(['sudo', 'hostnamectl', 'set-hostname', hostname], check=True)
                        subprocess.run(['sudo', 'sed', '-i', f's/127.0.1.1.*/127.0.1.1\t{hostname}/g', '/etc/hosts'], check=True)
                        success_message = f"Hostname updated to {hostname}. Reboot recommended."
                    except subprocess.CalledProcessError as e:
                        error_message = f"Failed to update system hostname: {str(e)}"
                else:
                    error_message = "Invalid hostname. Use only letters, numbers, and hyphens."
            
            # Update WiFi settings
            elif 'update_wifi' in request.form:
                wifi_ssid = request.form.get('wifi_ssid')
                wifi_password = request.form.get('wifi_password')
                wifi_auto_connect = 'wifi_auto_connect' in request.form
                
                if wifi_ssid:
                    # Save WiFi settings
                    Settings.set('wifi_ssid', wifi_ssid)
                    Settings.set('wifi_auto_connect', wifi_auto_connect)
                    
                    # Only update password if provided
                    if wifi_password:
                        Settings.set('wifi_password', wifi_password)
                    
                    # Update wpa_supplicant.conf if on Raspberry Pi
                    if _is_raspberry_pi():
                        try:
                            _update_wifi_config(wifi_ssid, wifi_password if wifi_password else Settings.get('wifi_password', ''))
                            success_message = "WiFi settings updated. Network will reconnect."
                        except Exception as e:
                            error_message = f"Failed to update WiFi configuration: {str(e)}"
                    else:
                        success_message = "WiFi settings saved (but not applied - not running on Raspberry Pi)"
                else:
                    error_message = "WiFi SSID is required"
            
            # Update IP settings
            elif 'update_ip' in request.form:
                use_dhcp = 'use_dhcp' in request.form
                
                # Save DHCP setting
                Settings.set('use_dhcp', use_dhcp)
                
                if not use_dhcp:
                    # Save static IP settings
                    static_ip = request.form.get('static_ip')
                    subnet_mask = request.form.get('subnet_mask')
                    default_gateway = request.form.get('default_gateway')
                    dns_server = request.form.get('dns_server')
                    
                    if static_ip and subnet_mask and default_gateway:
                        # Validate IP addresses
                        if _validate_ip_address(static_ip) and _validate_ip_address(default_gateway) and _validate_subnet_mask(subnet_mask):
                            Settings.set('static_ip', static_ip)
                            Settings.set('subnet_mask', subnet_mask)
                            Settings.set('default_gateway', default_gateway)
                            Settings.set('dns_server', dns_server if _validate_ip_address(dns_server) else '8.8.8.8')
                            
                            # Update the dhcpcd.conf file if on Raspberry Pi
                            if _is_raspberry_pi():
                                try:
                                    _update_ip_config(use_dhcp, static_ip, subnet_mask, default_gateway, dns_server)
                                    success_message = "IP configuration updated. Network will reconnect."
                                except Exception as e:
                                    error_message = f"Failed to update IP configuration: {str(e)}"
                            else:
                                success_message = "IP settings saved (but not applied - not running on Raspberry Pi)"
                        else:
                            error_message = "Invalid IP address or subnet mask format"
                    else:
                        error_message = "Static IP, subnet mask, and default gateway are required"
                else:
                    # If switching to DHCP, update configuration
                    if _is_raspberry_pi():
                        try:
                            _update_ip_config(use_dhcp)
                            success_message = "DHCP enabled. Network will reconnect."
                        except Exception as e:
                            error_message = f"Failed to update IP configuration: {str(e)}"
                    else:
                        success_message = "DHCP setting saved (but not applied - not running on Raspberry Pi)"
        except Exception as e:
            error_message = f"Error: {str(e)}"

    # Get current network settings
    network = {
        'hostname': Settings.get('hostname', platform.node()),
        'wifi_ssid': Settings.get('wifi_ssid', ''),
        'wifi_auto_connect': Settings.get('wifi_auto_connect', True),
        'use_dhcp': Settings.get('use_dhcp', True),
        'static_ip': Settings.get('static_ip', ''),
        'subnet_mask': Settings.get('subnet_mask', '255.255.255.0'),
        'default_gateway': Settings.get('default_gateway', ''),
        'dns_server': Settings.get('dns_server', '8.8.8.8'),
    }
    
    # Get current network status
    try:
        # Get current IP and MAC address
        ifaces = _get_network_interfaces()
        primary_iface = _get_primary_interface()
        
        if primary_iface and primary_iface in ifaces:
            network['current_ip'] = ifaces[primary_iface].get('ip', 'Not connected')
            network['mac_address'] = ifaces[primary_iface].get('mac', 'Unknown')
        else:
            network['current_ip'] = 'Not connected'
            network['mac_address'] = 'Unknown'
        
        # Get current WiFi info
        wifi_info = _get_wifi_info()
        network['connected_ssid'] = wifi_info.get('ssid', None)
        network['signal_strength'] = wifi_info.get('signal', 'Unknown')
        
        # Check internet connectivity
        network['internet_access'] = _check_internet_connectivity()
    except Exception as e:
        network['current_ip'] = 'Error'
        network['mac_address'] = 'Error'
        network['connected_ssid'] = None
        network['signal_strength'] = 'Error'
        network['internet_access'] = False
    
    return render_template(
        'settings/network.html',
        network=network,
        success_message=success_message,
        error_message=error_message
    )

@settings_bp.route('/scan_networks', methods=['GET'])
def scan_networks():
    """Scan for available WiFi networks"""
    try:
        networks = _scan_wifi_networks()
        return jsonify({'success': True, 'networks': networks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/run_diagnostics', methods=['GET'])
def run_diagnostics():
    """Run network diagnostics"""
    try:
        output = _run_network_diagnostics()
        return jsonify({'success': True, 'output': output})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/restart_network', methods=['POST'])
def restart_network():
    """Restart networking services"""
    try:
        if _is_raspberry_pi():
            subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'], check=True)
            return jsonify({'success': True, 'message': 'Network services restarted'})
        else:
            return jsonify({'success': False, 'message': 'Not running on Raspberry Pi'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Helper functions for network configuration
def _is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi' in model
    except:
        return False

def _validate_ip_address(ip):
    """Validate IP address format"""
    try:
        socket.inet_aton(ip)
        return True
    except:
        return False

def _validate_subnet_mask(mask):
    """Validate subnet mask format"""
    try:
        socket.inet_aton(mask)
        return True
    except:
        return False

def _get_network_interfaces():
    """Get information about all network interfaces"""
    interfaces = {}
    
    try:
        for iface in netifaces.interfaces():
            # Skip loopback
            if iface == 'lo':
                continue
                
            info = {'name': iface}
            
            # Get IP address
            addresses = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addresses:
                info['ip'] = addresses[netifaces.AF_INET][0]['addr']
            else:
                info['ip'] = None
                
            # Get MAC address
            if netifaces.AF_LINK in addresses:
                info['mac'] = addresses[netifaces.AF_LINK][0]['addr']
            else:
                info['mac'] = None
                
            interfaces[iface] = info
    except Exception:
        pass
        
    return interfaces

def _get_primary_interface():
    """Get the primary network interface"""
    try:
        # Try to get the interface with the default route
        gateways = netifaces.gateways()
        if 'default' in gateways and netifaces.AF_INET in gateways['default']:
            return gateways['default'][netifaces.AF_INET][1]
    except:
        pass
    
    # Fallback to wlan0 or eth0
    interfaces = netifaces.interfaces()
    if 'wlan0' in interfaces:
        return 'wlan0'
    elif 'eth0' in interfaces:
        return 'eth0'
        
    # Return the first non-loopback interface
    for iface in interfaces:
        if iface != 'lo':
            return iface
            
    return None

def _get_wifi_info():
    """Get information about the current WiFi connection"""
    info = {'ssid': None, 'signal': None}
    
    try:
        if _is_raspberry_pi():
            # Get SSID
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                info['ssid'] = result.stdout.strip()
                
            # Get signal strength
            result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
            if result.returncode == 0:
                match = re.search(r'Signal level=(-\d+) dBm', result.stdout)
                if match:
                    # Convert dBm to percentage (roughly)
                    dbm = int(match.group(1))
                    quality = min(100, max(0, 2 * (dbm + 100)))
                    info['signal'] = f"{quality}%"
    except:
        pass
        
    return info

def _check_internet_connectivity():
    """Check if there is internet connectivity"""
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def _update_wifi_config(ssid, password):
    """Update the WiFi configuration file"""
    if not _is_raspberry_pi():
        return
        
    # Create the wpa_supplicant.conf content
    config = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
    
    # Write the configuration to a temporary file
    with open('/tmp/wpa_supplicant.conf', 'w') as f:
        f.write(config)
        
    # Move the file to the correct location (requires sudo)
    subprocess.run(['sudo', 'mv', '/tmp/wpa_supplicant.conf', '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
    subprocess.run(['sudo', 'chmod', '600', '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
    
    # Restart networking
    subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'], check=True)

def _update_ip_config(use_dhcp, static_ip=None, subnet_mask=None, gateway=None, dns=None):
    """Update the IP configuration file"""
    if not _is_raspberry_pi():
        return
        
    # Create dhcpcd.conf content
    if use_dhcp:
        config = """# NuTetra Controller Network Configuration
# Generated automatically - do not edit manually

# Use DHCP by default
hostname
clientid
persistent
option rapid_commit
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
option interface_mtu
require dhcp_server_identifier
slaac private
"""
    else:
        # Calculate prefix length from subnet mask
        prefix_len = sum([bin(int(x)).count('1') for x in subnet_mask.split('.')])
        
        config = f"""# NuTetra Controller Network Configuration
# Generated automatically - do not edit manually

# Static IP configuration
interface wlan0
static ip_address={static_ip}/{prefix_len}
static routers={gateway}
static domain_name_servers={dns}

interface eth0
static ip_address={static_ip}/{prefix_len}
static routers={gateway}
static domain_name_servers={dns}
"""
    
    # Write the configuration to a temporary file
    with open('/tmp/dhcpcd.conf', 'w') as f:
        f.write(config)
        
    # Move the file to the correct location (requires sudo)
    subprocess.run(['sudo', 'mv', '/tmp/dhcpcd.conf', '/etc/dhcpcd.conf'], check=True)
    
    # Restart networking
    subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)

def _scan_wifi_networks():
    """Scan for available WiFi networks"""
    networks = []
    
    try:
        if _is_raspberry_pi():
            # Scan for networks
            result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse output to get SSID and signal strength
                for cell in result.stdout.split('Cell '):
                    if 'ESSID:' in cell:
                        ssid_match = re.search(r'ESSID:"([^"]*)"', cell)
                        if ssid_match and ssid_match.group(1):
                            ssid = ssid_match.group(1)
                            
                            # Get signal strength
                            signal_match = re.search(r'Signal level=(-\d+) dBm', cell)
                            if signal_match:
                                dbm = int(signal_match.group(1))
                                quality = min(100, max(0, 2 * (dbm + 100)))
                            else:
                                quality = 0
                                
                            networks.append({
                                'ssid': ssid,
                                'signal': quality
                            })
        else:
            # Mock data for testing
            networks = [
                {'ssid': 'Home Network', 'signal': 90},
                {'ssid': 'Neighbor Network', 'signal': 65},
                {'ssid': 'Guest Network', 'signal': 45}
            ]
            
        # Sort by signal strength
        networks.sort(key=lambda x: x['signal'], reverse=True)
        
        # Remove duplicates
        unique_networks = []
        seen_ssids = set()
        for network in networks:
            if network['ssid'] not in seen_ssids:
                unique_networks.append(network)
                seen_ssids.add(network['ssid'])
                
        return unique_networks
    except Exception as e:
        return [{'ssid': f'Error scanning: {str(e)}', 'signal': 0}]

def _run_network_diagnostics():
    """Run network diagnostics commands"""
    output = "Network Diagnostics Report\n"
    output += "========================\n\n"
    
    try:
        # Add hostname info
        output += f"Hostname: {platform.node()}\n"
        
        # Add interface info
        output += "\nNetwork Interfaces:\n"
        interfaces = _get_network_interfaces()
        for name, info in interfaces.items():
            output += f"  {name}:\n"
            output += f"    IP Address: {info.get('ip', 'Not assigned')}\n"
            output += f"    MAC Address: {info.get('mac', 'Unknown')}\n"
        
        # Add WiFi info
        wifi_info = _get_wifi_info()
        output += "\nWiFi Status:\n"
        output += f"  Connected to: {wifi_info.get('ssid', 'Not connected')}\n"
        output += f"  Signal Strength: {wifi_info.get('signal', 'Unknown')}\n"
        
        # Add ping test
        output += "\nConnectivity Tests:\n"
        
        # Ping router
        router = None
        try:
            gateways = netifaces.gateways()
            if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                router = gateways['default'][netifaces.AF_INET][0]
        except:
            pass
            
        if router:
            output += f"  Pinging router ({router}):\n"
            result = subprocess.run(['ping', '-c', '3', router], capture_output=True, text=True)
            if result.returncode == 0:
                output += "    Success\n"
            else:
                output += f"    Failed: {result.stdout}\n"
        
        # Ping Google DNS
        output += "  Pinging Google DNS (8.8.8.8):\n"
        result = subprocess.run(['ping', '-c', '3', '8.8.8.8'], capture_output=True, text=True)
        if result.returncode == 0:
            output += "    Success\n"
        else:
            output += f"    Failed: {result.stdout}\n"
        
        # DNS lookup
        output += "  DNS Lookup (google.com):\n"
        result = subprocess.run(['nslookup', 'google.com'], capture_output=True, text=True)
        if result.returncode == 0:
            output += "    Success\n"
        else:
            output += f"    Failed: {result.stdout}\n"
        
        return output
    except Exception as e:
        return f"Error running diagnostics: {str(e)}" 