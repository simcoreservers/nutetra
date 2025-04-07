#!/usr/bin/env python3
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()
    # Use environment variables or default to localhost:5000
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Run in debug mode for development, production for... production
    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        # In production, use Flask's built-in WSGI server with threading
        # For actual production deployment, consider using gunicorn
        app.run(host=host, port=port, threaded=True) 