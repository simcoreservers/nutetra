from app import create_app, db
import sqlite3
import os

def migrate():
    app = create_app()
    with app.app_context():
        # Get database path from app config
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(pumps)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns if they don't exist
        if 'nutrient_brand' not in columns:
            cursor.execute("ALTER TABLE pumps ADD COLUMN nutrient_brand VARCHAR(50)")
            print("Added nutrient_brand column")
            
        if 'nutrient_name' not in columns:
            cursor.execute("ALTER TABLE pumps ADD COLUMN nutrient_name VARCHAR(100)")
            print("Added nutrient_name column")
            
        if 'nitrogen_pct' not in columns:
            cursor.execute("ALTER TABLE pumps ADD COLUMN nitrogen_pct FLOAT")
            print("Added nitrogen_pct column")
            
        if 'phosphorus_pct' not in columns:
            cursor.execute("ALTER TABLE pumps ADD COLUMN phosphorus_pct FLOAT")
            print("Added phosphorus_pct column")
            
        if 'potassium_pct' not in columns:
            cursor.execute("ALTER TABLE pumps ADD COLUMN potassium_pct FLOAT")
            print("Added potassium_pct column")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate() 