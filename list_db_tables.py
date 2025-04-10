from app import create_app
import sqlite3
import os

def list_tables():
    """List all tables in the database"""
    app = create_app()
    
    # Get database path from app config
    db_path = os.path.join(app.root_path, 'nutetra.db')
    
    print(f"Connecting to database at {db_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query to list all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            print("Tables in the database:")
            for table in tables:
                print(f" - {table[0]}")
                
                # Also print schema for each table
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                print(f"   Columns in {table[0]}:")
                for col in columns:
                    print(f"     {col[1]} ({col[2]})")
        else:
            print("No tables found in the database.")
            
        # Close connection
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables() 