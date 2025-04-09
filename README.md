# NuTetra - Hydroponic System Controller

NuTetra is a comprehensive hydroponic system controller that manages nutrient dosing, pH balancing, and environmental monitoring.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/nutetra.git
cd nutetra
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize the Database

```bash
python initialize_db.py
```

This will create the database with all required tables and default data, including:
- Nutrient brands and products
- Default settings for pH, EC, temperature, and humidity
- Default pumps (Nutrient, pH Up, pH Down)

### Step 5: Run the Application

```bash
python run.py
```

The application will be available at http://localhost:5000

## Features

- **Nutrient Management**: Configure and control nutrient dosing pumps
- **pH Balancing**: Automatic pH adjustment with up/down solutions
- **Environmental Monitoring**: Track temperature, humidity, and water levels
- **Scheduling**: Set up automated watering and nutrient dosing schedules
- **User Interface**: Web-based dashboard for easy control and monitoring

## Configuration

### Hardware Setup

1. Connect your pumps to the specified GPIO pins:
   - Nutrient Pump: GPIO 17
   - pH Up Pump: GPIO 27
   - pH Down Pump: GPIO 22

2. Connect your sensors:
   - pH Sensor: GPIO 23
   - EC Sensor: GPIO 24
   - Temperature Sensor: GPIO 25
   - Humidity Sensor: GPIO 26

### Software Configuration

Most settings can be configured through the web interface. For advanced configuration, edit the `config.py` file.

## Troubleshooting

### Database Issues

If you encounter database-related errors:

1. Stop the application
2. Run the initialization script again:
   ```bash
   python initialize_db.py
   ```
3. Restart the application

### Pump Control Issues

1. Check that the pumps are connected to the correct GPIO pins
2. Verify that the pumps are enabled in the web interface
3. Check the flow rate settings

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [Chart.js](https://www.chartjs.org/)
- [Socket.IO](https://socket.io/)
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) 