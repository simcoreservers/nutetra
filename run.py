#!/usr/bin/env python3
"""
NuTetra Controller - Run Script
Launch the NuTetra Controller application
"""

import os
import sys
import logging
from app import create_app, socketio

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, 'nutetra.log'), mode='a')
    ]
)

# Create Flask app
app = create_app()

# There's no need to initialize Socket.IO here since it's now
# properly initialized in the create_app function

if __name__ == '__main__':
    # Check if running on a Raspberry Pi
    try:
        import lgpio
        is_raspberry_pi = True
        logging.info("Running on Raspberry Pi - Hardware features enabled")
    except (ImportError, RuntimeError):
        is_raspberry_pi = False
        logging.warning("Not running on Raspberry Pi - Hardware features will be simulated")
    
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    
    # Get host from environment or use default
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Start the server with Socket.IO
    logging.info(f"Starting NuTetra Controller on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=True if os.environ.get('FLASK_ENV') == 'development' else False) 