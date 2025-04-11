from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
from apscheduler.schedulers.background import BackgroundScheduler
import os
import click

# Initialize extensions
db = SQLAlchemy()
scheduler = BackgroundScheduler()
# We will not initialize socketio here anymore since it will be created in run.py

# Import Flask CLI command for database initialization
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Create all database tables."""
    db.create_all()
    click.echo('Initialized the database.')
    
    # Initialize default settings
    from app.models.settings import Settings
    Settings.initialize_defaults()
    click.echo('Initialized default settings.')
    
    # Initialize default pumps
    from app.models.pump import Pump
    Pump.initialize_defaults()
    click.echo('Initialized default pumps.')

def register_template_helpers(app):
    """Register template helpers like filters and context processors"""
    
    # Register filters
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        """Format a datetime object."""
        if value is None:
            return ""
        return value.strftime(format)
        
    @app.template_filter('ph')
    def format_ph(value):
        """Format pH value with 2 decimal places."""
        if value is None:
            return "N/A"
        return f"{value:.2f}"
        
    @app.template_filter('ec')
    def format_ec(value):
        """Format EC value with appropriate units."""
        if value is None:
            return "N/A"
        return f"{value:.0f} μS/cm"
        
    @app.template_filter('temp')
    def format_temp(value):
        """Format temperature value with 1 decimal place."""
        if value is None:
            return "N/A"
        return f"{value:.1f}°C"
    
    # Register context processors
    @app.context_processor
    def inject_template_globals():
        """Make global functions and variables available to all templates"""
        from app.models.settings import Settings
        from app.utils.sensor_manager import get_last_reading
        from app.models.notification import Notification
        from flask import request
        
        def get_sensor_status(sensor_type):
            """Get connection status of a sensor"""
            reading = get_last_reading(sensor_type)
            return "connected" if reading is not None else "disconnected"
            
        def get_recent_notifications(limit=5):
            """Get recent notifications"""
            return Notification.get_all(limit=limit)
            
        def is_active_page(endpoint):
            """Check if the given endpoint is the current page"""
            return request.endpoint and request.endpoint.startswith(endpoint)
            
        def get_growth_phase_for_week(profile, week):
            """Get the growth phase label for a specific week"""
            growth_phases_text = profile.get('growth_phases', '')
            
            if not growth_phases_text:
                # Default phases if not defined
                if week <= 3:
                    return "Seedling"
                elif week <= 6:
                    return "Vegetative"
                else:
                    return "Flowering"
            
            # Parse the growth phases text
            # Expected format: "Seedling: 1-3, Vegetative: 4-6, Flowering: 7-12"
            phases = {}
            for phase_entry in growth_phases_text.split(','):
                if ':' in phase_entry:
                    phase_name, weeks_range = phase_entry.split(':', 1)
                    phase_name = phase_name.strip()
                    
                    for week_range in weeks_range.split(','):
                        week_range = week_range.strip()
                        if '-' in week_range:
                            start, end = map(int, week_range.split('-'))
                            for w in range(start, end + 1):
                                phases[w] = phase_name
                        else:
                            try:
                                w = int(week_range)
                                phases[w] = phase_name
                            except ValueError:
                                pass
            
            return phases.get(week, "Unknown")
        
        return {
            'settings': Settings,
            'get_last_reading': get_last_reading,
            'get_sensor_status': get_sensor_status,
            'get_recent_notifications': get_recent_notifications,
            'is_active_page': is_active_page,
            'get_growth_phase_for_week': get_growth_phase_for_week
        }

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Register template helpers
    register_template_helpers(app)
    
    # Set configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'DATABASE_URL', 'sqlite:///' + os.path.join(app.instance_path, 'nutetra.sqlite')
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize database
    db.init_app(app)
    
    # Instead of initializing Socket.IO here, we'll do it in run.py
    # This avoids circular import issues
    
    # Start the scheduler with Flask app context
    if not scheduler.running:
        # Store app reference for scheduled tasks to use
        scheduler._app = app
        scheduler.start()

    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.api import api_bp
    from app.controllers.sensors import sensors_bp
    from app.controllers.dosing import dosing_bp
    from app.controllers.settings import settings_bp
    from app.controllers.garden import garden_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)  # URL prefix is defined in the blueprint
    app.register_blueprint(sensors_bp, url_prefix='/sensors')
    app.register_blueprint(garden_bp, url_prefix='/garden')
    app.register_blueprint(dosing_bp, url_prefix='/hardware')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Initialize sensors and dosing systems
    with app.app_context():
        from app.utils.sensor_manager import init_sensors
        from app.utils.dosing_manager import init_dosing
        from app.models.nutrient import NutrientBrand
        
        db.create_all()
        init_sensors()
        init_dosing()
        
        # Initialize nutrient brands and products
        NutrientBrand.initialize_defaults()
        
    # Register the database command
    app.cli.add_command(init_db_command)

    # Add application teardown handler to clean up scheduler
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        if scheduler.running:
            # Only shutdown when the application is terminating
            if app.config.get('ENV') != 'development' and exception is None:
                scheduler.shutdown()
    
    return app 