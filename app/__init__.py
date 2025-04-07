from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
from apscheduler.schedulers.background import BackgroundScheduler
import os
import click

# Initialize extensions
db = SQLAlchemy()
scheduler = BackgroundScheduler()

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

# Add Jinja2 filters
def register_jinja_filters(app):
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        """Format a datetime object."""
        if value is None:
            return ""
        return value.strftime(format)

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Register Jinja2 filters
    register_jinja_filters(app)
    
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
    
    # Initialize Socket.IO with our custom manager
    from app.utils.socketio_manager import init_socketio
    socketio = init_socketio(app)
    
    # Start the scheduler
    if not scheduler.running:
        scheduler.start()

    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.api import api_bp
    from app.controllers.sensors import sensors_bp
    from app.controllers.dosing import dosing_bp
    from app.controllers.settings import settings_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)  # URL prefix is defined in the blueprint
    app.register_blueprint(sensors_bp, url_prefix='/sensors')
    app.register_blueprint(dosing_bp, url_prefix='/dosing')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Initialize sensors and dosing systems
    with app.app_context():
        from app.utils.sensor_manager import init_sensors
        from app.utils.dosing_manager import init_dosing
        
        db.create_all()
        init_sensors()
        init_dosing()
        
    # Register the database command
    app.cli.add_command(init_db_command)

    return app 