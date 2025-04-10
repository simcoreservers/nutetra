from app import create_app
import sqlite3
import os

def migrate_db():
    """Add nutrient_type column to nutrient_products table"""
    app = create_app()
    
    # Get database path from app config
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    
    print(f"Connecting to database at {db_path}")
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, check if the nutrient_brands table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nutrient_brands'")
    if not cursor.fetchone():
        print("The nutrient_brands table doesn't exist. Creating tables...")
        # Trigger SQLAlchemy to create all tables including our new models
        with app.app_context():
            from app import db
            from app.models.nutrient import NutrientBrand, NutrientProduct
            db.create_all()
            print("Database tables created.")
            NutrientBrand.initialize_defaults()
            print("Default nutrient brands initialized.")
    
    # Now check if the nutrient_type column exists in nutrient_products
    cursor.execute("PRAGMA table_info(nutrient_products)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'nutrient_type' not in column_names:
        print("Adding nutrient_type column to nutrient_products table...")
        
        # Add the column
        cursor.execute("ALTER TABLE nutrient_products ADD COLUMN nutrient_type TEXT")
        
        # Set default values based on product names
        print("Setting default values based on product names...")
        
        # Get all product records
        cursor.execute("SELECT id, name FROM nutrient_products")
        products = cursor.fetchall()
        
        updates = 0
        for product_id, name in products:
            name_lower = name.lower()
            nutrient_type = 'other'
            
            # Determine the nutrient type based on the name
            if ('cal' in name_lower and 'mag' in name_lower) or ('calmag' in name_lower):
                nutrient_type = 'calmag'
            elif 'micro' in name_lower:
                nutrient_type = 'micro'
            elif ('grow' in name_lower) or ('gro' in name_lower) or ('veg' in name_lower):
                nutrient_type = 'grow'
            elif ('bloom' in name_lower) or ('flower' in name_lower):
                nutrient_type = 'bloom'
            
            # Update the record
            cursor.execute(
                "UPDATE nutrient_products SET nutrient_type = ? WHERE id = ?", 
                (nutrient_type, product_id)
            )
            updates += 1
        
        # Commit changes
        conn.commit()
        print(f"Updated {updates} products with nutrient types")
    else:
        print("nutrient_type column already exists.")
    
    # Close connection
    conn.close()
    print("Migration completed successfully")

if __name__ == "__main__":
    migrate_db() 