#!/usr/bin/env python
"""
Database Initialization Script for NuTetra

This script initializes the database with all required entries.
It can be run independently to reset or initialize the database.
"""

import os
import sys
from app import create_app, db
from app.models.nutrient import NutrientBrand, NutrientProduct
from app.models.settings import Settings
from app.models.pump import Pump

def initialize_database():
    """Initialize the database with all required entries."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Initialize nutrient brands and products
        print("Initializing nutrient brands and products...")
        NutrientBrand.initialize_defaults()
        
        # Initialize default settings
        print("Initializing default settings...")
        default_settings = [
            ('ph_target', '6.0'),
            ('ph_tolerance', '0.5'),
            ('ec_target', '1.8'),
            ('ec_tolerance', '0.2'),
            ('temperature_target', '22.0'),
            ('temperature_tolerance', '2.0'),
            ('humidity_target', '60.0'),
            ('humidity_tolerance', '5.0'),
            ('light_schedule_on', '06:00'),
            ('light_schedule_off', '18:00'),
            ('watering_interval', '3600'),  # 1 hour in seconds
            ('watering_duration', '30'),    # 30 seconds
            ('nutrient_schedule', '86400'), # 24 hours in seconds
            ('nutrient_duration', '60'),    # 60 seconds
            ('ph_check_interval', '3600'),  # 1 hour in seconds
            ('ec_check_interval', '3600'),  # 1 hour in seconds
            ('temperature_check_interval', '300'),  # 5 minutes in seconds
            ('humidity_check_interval', '300'),     # 5 minutes in seconds
        ]
        
        for key, value in default_settings:
            if not Settings.query.filter_by(key=key).first():
                Settings(key=key, value=value).save()
                print(f"  Created setting: {key} = {value}")
        
        # Initialize default pumps
        print("Initializing default pumps...")
        default_pumps = [
            {
                'name': 'Nutrient Pump 1',
                'type': 'nutrient',
                'gpio_pin': 17,
                'flow_rate': 1.0,
                'enabled': True
            },
            {
                'name': 'pH Up Pump',
                'type': 'ph_up',
                'gpio_pin': 27,
                'flow_rate': 0.5,
                'enabled': True
            },
            {
                'name': 'pH Down Pump',
                'type': 'ph_down',
                'gpio_pin': 22,
                'flow_rate': 0.5,
                'enabled': True
            }
        ]
        
        for pump_data in default_pumps:
            if not Pump.query.filter_by(name=pump_data['name']).first():
                pump = Pump(**pump_data)
                pump.save()
                print(f"  Created pump: {pump.name}")
        
        print("\nDatabase initialization complete!")

if __name__ == '__main__':
    # Check if the database file exists
    db_path = os.path.join('instance', 'nutetra.db')
    if os.path.exists(db_path):
        response = input(f"Database file already exists at {db_path}. Do you want to reinitialize it? (y/n): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    initialize_database() 