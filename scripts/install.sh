#!/bin/bash

# Exit on error
set -e

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo bash scripts/install.sh)"
  exit 1
fi

echo "============================================="
echo "  NuTetra Controller Installation Script"
echo "============================================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Navigate to the parent directory (project root)
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "Installing system dependencies..."
apt update
apt install -y python3-pip python3-venv python3-dev
apt install -y libatlas-base-dev # for numpy
apt install -y i2c-tools
apt install -y sqlite3
apt install -y libopenjp2-7 # for Pillow
apt install -y unclutter  # To hide mouse cursor in kiosk mode
apt install -y xserver-xorg x11-xserver-utils xinit chromium-browser
apt install -y dnsutils # for nslookup and other network diagnostic tools

echo "Enabling I2C interface..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
fi

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt

# Create database
echo "Setting up database..."
mkdir -p instance
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"

# Set up autostart
echo "Configuring autostart..."
mkdir -p /home/pi/.config/autostart
cat > /home/pi/.config/autostart/nutetra.desktop << EOF
[Desktop Entry]
Type=Application
Name=NuTetra Controller
Exec=/bin/bash ${PROJECT_DIR}/scripts/start.sh
X-GNOME-Autostart-enabled=true
EOF

# Create start script
echo "Creating start script..."
cat > ${PROJECT_DIR}/scripts/start.sh << EOF
#!/bin/bash
cd ${PROJECT_DIR}
source venv/bin/activate
python run.py
EOF
chmod +x ${PROJECT_DIR}/scripts/start.sh

# Set up kiosk mode
echo "Setting up kiosk mode for touchscreen..."
cat > /home/pi/.config/autostart/kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=Kiosk Mode
Exec=/bin/bash ${PROJECT_DIR}/scripts/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF

# Create kiosk script
cat > ${PROJECT_DIR}/scripts/kiosk.sh << EOF
#!/bin/bash
xset -dpms      # Disable DPMS (Energy Star) features
xset s off      # Disable screen saver
xset s noblank  # Don't blank the screen

unclutter &     # Hide mouse cursor

# Wait for the app to start
sleep 5

# Start Chromium in kiosk mode
chromium-browser --noerrdialogs --kiosk http://localhost:5000 --incognito --disable-translate
EOF
chmod +x ${PROJECT_DIR}/scripts/kiosk.sh

# Create service file
echo "Creating systemd service..."
cat > /etc/systemd/system/nutetra.service << EOF
[Unit]
Description=NuTetra Controller Service
After=network.target

[Service]
User=pi
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/run.py
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=nutetra

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl enable nutetra.service
systemctl start nutetra.service

echo "============================================="
echo "NuTetra Controller installed successfully!"
echo "System will reboot in 5 seconds..."
echo "============================================="

sleep 5
reboot 