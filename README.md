# NuTetra Controller

A complete hydroponics automation system for the Raspberry Pi 5, designed to monitor and control nutrient solutions for optimal plant growth.

![NuTetra Controller Logo](app/static/img/logo.svg)

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Software Architecture](#software-architecture)
- [Installation](#installation)
- [Configuration Guide](#configuration-guide)
- [Hardware Setup](#hardware-setup)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [License](#license)

## Overview

NuTetra Controller is a comprehensive hydroponics automation system designed specifically for the Raspberry Pi 5. It provides real-time monitoring of essential parameters (pH, EC, temperature), automated nutrient and pH adjustment dosing, and an intuitive web interface for control and visualization.

The system is designed for both hobbyist and commercial hydroponics setups, with features to help optimize plant growth and reduce manual intervention.

## Features

- **Monitoring System**
  - Real-time pH, EC (electrical conductivity), and temperature monitoring
  - Customizable alert thresholds and notifications
  - Historical data tracking with trend analysis
  
- **Dosing Automation**
  - Precise multi-channel peristaltic pump control
  - Automated nutrient and pH adjustment based on sensor readings
  - Manual dosing capabilities for testing and calibration
  
- **Plant Profiles**
  - Pre-configured profiles for different plant types (leafy greens, fruiting plants, etc.)
  - Customizable grow cycle scheduling with week-by-week nutrient adjustments
  - User-defined custom profiles for specialized crops
  
- **User Interface**
  - Modern, responsive web interface with dark theme
  - Mobile-optimized controls for on-the-go monitoring
  - Interactive data visualization with Chart.js
  - Touch-screen compatible for Raspberry Pi displays
  
- **Advanced Features**
  - Notification system (web, email, SMS via Twilio)
  - Backup and restore functionality for system settings
  - External API for integration with other systems
  - Multi-stage grow cycle programming

## Hardware Requirements

### Core Components
- Raspberry Pi 5 (recommended) or Raspberry Pi 4 with 2GB+ RAM
- Micro SD card (16GB+ recommended)
- 5V power supply for Raspberry Pi (3A+ recommended)
- Internet connection (Wi-Fi or Ethernet)

### Sensors
- pH sensor (compatible with Atlas Scientific pH EZO or similar)
- EC/TDS sensor (compatible with Atlas Scientific EC EZO or similar)
- Temperature sensor (DS18B20 waterproof probe or similar)
- I2C interface for sensors

### Dosing System
- Peristaltic pumps (minimum 4 recommended):
  - 2 for pH adjustments (up/down)
  - 2+ for nutrient solutions
- Pump driver board or relay module
- Food-grade tubing and fittings

### Optional Components
- 7" Raspberry Pi touchscreen display for local control
- Float switches for reservoir level monitoring
- Additional relays for controlling lights, pumps, and fans
- Waterproof enclosure for the electronics

## Software Architecture

NuTetra runs on a Flask-based web application with the following components:

- **Backend**: Python 3.7+ with Flask framework
- **Database**: SQLite for data storage
- **Real-time Updates**: Socket.IO for live data streaming
- **Scheduled Tasks**: APScheduler for automated operations
- **Hardware Interface**: lgpio for Raspberry Pi GPIO control
- **Frontend**: HTML/CSS/JavaScript with a responsive design

## Installation

### Method 1: Automated Installation (Recommended)

The easiest way to install NuTetra Controller is using our installation script:

1. Clone the repository:
```bash
git clone https://github.com/simcoreservers/nutetra.git
cd nutetra
```

2. Run the installation script as root:
```bash
sudo bash scripts/install.sh
```

This script will:
- Install all required system dependencies
- Set up a Python virtual environment
- Install Python package dependencies
- Configure the database
- Set up systemd service for automatic startup
- Configure the system for kiosk mode if a display is connected
- Reboot the system to apply changes

### Method 2: Manual Installation

For more control over the installation process:

1. Clone the repository:
```bash
git clone https://github.com/simcoreservers/nutetra.git
cd nutetra
```

2. Install system dependencies:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y libatlas-base-dev i2c-tools sqlite3 libopenjp2-7
```

3. Enable I2C interface (if using I2C sensors):
```bash
sudo raspi-config nonint do_i2c 0
```

4. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

5. Install Python dependencies:
```bash
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
```

6. Create the database:
```bash
mkdir -p instance
flask init-db
```

7. Set up systemd service for automatic startup:
```bash
sudo nano /etc/systemd/system/nutetra.service
```

Add the following content (adjust paths as needed):
```
[Unit]
Description=NuTetra Controller Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/nutetra
ExecStart=/home/pi/nutetra/venv/bin/python /home/pi/nutetra/run.py
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=nutetra

[Install]
WantedBy=multi-user.target
```

8. Enable and start the service:
```bash
sudo systemctl enable nutetra.service
sudo systemctl start nutetra.service
```

### Method 3: Docker Installation

For deployment in a containerized environment:

1. Clone the repository:
```bash
git clone https://github.com/simcoreservers/nutetra.git
cd nutetra
```

2. Build and run the Docker container:
```bash
docker build -t nutetra .
docker run -p 5000:5000 --privileged -v nutetra_data:/app/instance nutetra
```

Note: The `--privileged` flag is required for GPIO access.

## Configuration Guide

### Initial Setup

1. Access the web interface at `http://raspberrypi.local:5000` or the IP address of your Raspberry Pi
2. Log in with the default credentials:
   - Username: `admin`
   - Password: `nutetra`
   - You'll be prompted to change these on first login

### System Settings

Navigate to Settings > System to configure:

- **Network**: Wi-Fi settings, hostname, and network diagnostics
  - Configure Wi-Fi network connection (SSID and password)
  - Set static IP address for reliable remote access
  - Modify hostname (default: raspberrypi.local)
  - Enable/disable remote access options
  - Run network diagnostics and connectivity tests
- **Time Zone**: Set your local time zone for accurate scheduling
- **Backup/Restore**: Create or restore system backups
- **System Updates**: Check for and apply software updates
- **Power Management**: Configure power-saving options and scheduled reboots

### Sensor Configuration

1. Navigate to Sensors > Configuration
2. For each sensor:
   - Assign the correct I2C address or GPIO pin
   - Set reading frequency and averaging parameters
   - Configure alert thresholds for notifications

### Pump Setup

1. Navigate to Hardware > Pumps
2. For each pump:
   - Assign a name and function (pH Up, pH Down, Nutrient A, etc.)
   - Set the GPIO pin controlling the pump
   - Calibrate flow rate (ml/min)
   - Configure safety limits (maximum dose)

### Nutrient Profiles

1. Navigate to Garden > Plant Profiles
2. Select from pre-configured profiles or create custom ones
3. Configure:
   - Target pH, EC, and temperature ranges
   - Nutrient ratios and dosing sequences
   - Growth cycle schedules (for plants with distinct growth phases)

### Notification Setup

1. Navigate to Settings > Notifications
2. Configure notification methods:
   - Web interface alerts (always enabled)
   - Email notifications (requires SMTP settings)
   - SMS notifications (requires Twilio account)
3. Set notification triggers for sensor values, dosing events, and system alerts

## Hardware Setup

### Sensor Wiring

#### I2C Sensors (Atlas Scientific EZO circuits)
- Connect VCC to Raspberry Pi 3.3V or 5V (depending on sensor)
- Connect GND to Raspberry Pi GND
- Connect SDA to Raspberry Pi SDA (Pin 3)
- Connect SCL to Raspberry Pi SCL (Pin 5)

#### Temperature Sensor (DS18B20)
- Connect VCC to Raspberry Pi 3.3V
- Connect GND to Raspberry Pi GND
- Connect DATA to Raspberry Pi GPIO4 (Pin 7)
- Add a 4.7kΩ pull-up resistor between VCC and DATA

### Pump Wiring

#### Using a Relay Board
- Connect relay board VCC to Raspberry Pi 5V
- Connect relay board GND to Raspberry Pi GND
- Connect relay control pins to available GPIO pins
- Connect pump power through relay terminals

#### Using Direct GPIO Control (small DC pumps)
- Use a transistor or MOSFET driver circuit for each pump
- Connect driver circuit inputs to GPIO pins
- Add protection diodes to prevent voltage spikes

### Full Wiring Diagram
For detailed wiring diagrams, refer to the `docs/hardware_setup.pdf` in this repository.

## Usage Guide

### Dashboard
The main dashboard provides an overview of your system status, including:
- Current sensor readings
- Alert status
- Dosing system status
- Quick action buttons for common tasks

### Monitoring
The Monitoring section offers:
- Real-time sensor reading graphs
- Historical data visualization
- Data export options (CSV, JSON)
- Custom timeframe selection

### Garden Management
The Garden section allows you to:
- Select and configure plant profiles
- View and adjust nutrient schedules
- Track growth cycle progress
- Customize nutrient ratios

### Manual Control
For testing and maintenance:
- Trigger manual dosing for individual pumps
- Run sensor reading tests
- Calibrate sensors and pumps

## API Reference

NuTetra Controller provides a RESTful API for integration with other systems:

### Authentication
All API requests require authentication using an API key.
```
GET /api/v1/sensor-readings HTTP/1.1
Host: raspberrypi.local:5000
X-API-Key: your_api_key_here
```

### Endpoints

#### Sensor Data
- `GET /api/v1/sensor-readings` - Get current sensor readings
- `GET /api/v1/sensor-history?days=7` - Get historical sensor data
- `GET /api/v1/sensor-stats` - Get statistical data about readings

#### Control
- `POST /api/v1/dose` - Trigger manual dosing
- `POST /api/v1/set-profile` - Change active plant profile
- `POST /api/v1/calibrate` - Start sensor calibration process

#### System
- `GET /api/v1/system-status` - Get system status information
- `GET /api/v1/notifications` - Get recent notifications
- `POST /api/v1/reboot` - Reboot the system (requires admin API key)

Full API documentation is available at `http://raspberrypi.local:5000/api/docs` when the system is running.

## Development

### Project Structure
```
nutetra/
├── app/
│   ├── controllers/       # Route handlers for web interface
│   ├── models/            # Database models and data structures
│   ├── static/            # Static assets (CSS, JS, images)
│   │   ├── css/           # Stylesheets
│   │   ├── js/            # JavaScript files
│   │   └── img/           # Images and icons
│   ├── templates/         # HTML templates (Jinja2)
│   │   ├── sensors/       # Sensor-related templates
│   │   ├── garden/        # Garden management templates
│   │   └── settings/      # Settings templates
│   ├── utils/             # Utility functions and hardware interfaces
│   │   ├── sensor_manager.py  # Sensor reading and calibration
│   │   └── dosing_manager.py  # Pump control and dosing logic
│   └── __init__.py        # Application factory
├── instance/              # Instance-specific data (database, configs)
├── logs/                  # Application logs
├── scripts/               # Installation and utility scripts
├── tests/                 # Unit and integration tests
├── requirements.txt       # Python dependencies
├── run.py                 # Application entry point
└── README.md              # This documentation
```

### Development Environment

For development, we recommend setting up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
FLASK_ENV=development python run.py
```

#### Running Tests
```bash
pytest
```

### Contributing
Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## Troubleshooting

### Common Issues

#### Sensor Connection Problems
- **Symptom**: "No sensor readings" or "Sensor not found"
- **Solution**: 
  - Check I2C connections and addresses with `i2cdetect -y 1`
  - Verify sensor power supply is stable
  - Check for configuration errors in sensor setup

#### Pump Not Working
- **Symptom**: Pump doesn't activate when triggered
- **Solution**:
  - Test GPIO pin manually: `raspi-gpio set PIN_NUMBER op pv 1`
  - Verify relay or driver circuit connections
  - Check pump power supply
  - Inspect settings for maximum dosing limits

#### Web Interface Not Loading
- **Symptom**: Cannot access web interface
- **Solution**:
  - Check if service is running: `systemctl status nutetra.service`
  - Verify network connectivity: `ping raspberrypi.local`
  - Check logs for errors: `journalctl -u nutetra.service`
  - Restart service: `sudo systemctl restart nutetra.service`

### Log Files
Log files are stored in the `logs/` directory. The main logs are:
- `nutetra.log` - General application logs
- `sensor.log` - Sensor-specific logs
- `dosing.log` - Dosing system logs

View logs using:
```bash
tail -f logs/nutetra.log
```

Or view system service logs:
```bash
sudo journalctl -u nutetra.service -f
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- Calibrate pH sensor (if readings drift)
- Check and clean nutrient and pH solution tanks
- Verify all pump tubing for kinks or blockages

#### Monthly
- Calibrate EC sensor
- Back up system settings
- Clean sensor probes according to manufacturer's recommendations
- Check system logs for warning signs

#### Quarterly
- Replace peristaltic pump tubing
- Update software: `sudo apt update && sudo apt upgrade`
- Full system backup including database

### Updating the Software
```bash
cd /home/pi/nutetra
git pull
sudo systemctl restart nutetra.service
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Chart.js](https://www.chartjs.org/) - Interactive charts
- [Socket.IO](https://socket.io/) - Real-time communication
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [lgpio](https://abyz.me.uk/lg/py_lgpio.html) - Raspberry Pi GPIO control 