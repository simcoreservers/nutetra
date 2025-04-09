#!/usr/bin/env python
"""
Database Check Script for NuTetra

This script checks if the database is properly initialized with all required entries.
It can be used to diagnose database issues.
"""

import os
import sys
from app import create_app, db
from app.models.nutrient import NutrientBrand, NutrientProduct
from app.models.settings import Settings
from app.models.pump import Pump

def check_database():
    """Check if the database is properly initialized."""
    app = create_app()
    
    with app.app_context():
        # Check if tables exist
        print("Checking database tables...")
        tables = db.engine.table_names()
        required_tables = ['nutrient_brand', 'nutrient_product', 'settings', 'pump']
        
        missing_tables = [table for table in required_tables if table not in tables]
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            print("  Run 'python initialize_db.py' to create missing tables.")
            return False
        else:
            print("✅ All required tables exist.")
        
        # Check nutrient brands
        print("\nChecking nutrient brands...")
        brands = NutrientBrand.query.all()
        if not brands:
            print("❌ No nutrient brands found.")
            print("  Run 'python initialize_db.py' to initialize nutrient brands.")
            return False
        else:
            print(f"✅ Found {len(brands)} nutrient brands.")
            for brand in brands:
                print(f"  - {brand.name} ({len(brand.products)} products)")
        
        # Check settings
        print("\nChecking settings...")
        settings = Settings.query.all()
        required_settings = [
            'ph_target', 'ph_tolerance', 'ec_target', 'ec_tolerance',
            'temperature_target', 'temperature_tolerance', 'humidity_target', 'humidity_tolerance'
        ]
        
        missing_settings = []
        for key in required_settings:
            if not Settings.query.filter_by(key=key).first():
                missing_settings.append(key)
        
        if missing_settings:
            print(f"❌ Missing settings: {', '.join(missing_settings)}")
            print("  Run 'python initialize_db.py' to initialize settings.")
            return False
        else:
            print(f"✅ Found {len(settings)} settings.")
        
        # Check pumps
        print("\nChecking pumps...")
        pumps = Pump.query.all()
        required_pump_types = ['nutrient', 'ph_up', 'ph_down']
        
        missing_pump_types = []
        for pump_type in required_pump_types:
            if not Pump.query.filter_by(type=pump_type).first():
                missing_pump_types.append(pump_type)
        
        if missing_pump_types:
            print(f"❌ Missing pump types: {', '.join(missing_pump_types)}")
            print("  Run 'python initialize_db.py' to initialize pumps.")
            return False
        else:
            print(f"✅ Found {len(pumps)} pumps.")
            for pump in pumps:
                print(f"  - {pump.name} ({pump.type})")
        
        print("\n✅ Database check complete! All required entries exist.")
        return True

if __name__ == '__main__':
    db_path = os.path.join('instance', 'nutetra.db')
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}.")
        print("  Run 'python initialize_db.py' to create the database.")
        sys.exit(1)
    
    success = check_database()
    sys.exit(0 if success else 1) 