from app import create_app, db
from app.models.nutrient import NutrientProduct

def migrate_nutrient_types():
    """Add nutrient_type field to existing nutrient products and set default values"""
    app = create_app()
    with app.app_context():
        # Check if the nutrient_type column exists
        try:
            # Try to access the nutrient_type column
            first_product = NutrientProduct.query.first()
            if first_product:
                # Access the property to see if it raises an error
                _ = first_product.nutrient_type
                print("Nutrient type column already exists.")
            else:
                print("No nutrient products found in database.")
                return
        except Exception as e:
            print(f"Error checking nutrient_type column: {e}")
            print("You may need to create the column manually in the database.")
            return
        
        # Get all products
        products = NutrientProduct.query.all()
        updates = 0
        
        # Update each product based on name
        for product in products:
            name_lower = product.name.lower()
            
            # Skip products that already have a nutrient_type
            if product.nutrient_type is not None:
                continue
                
            # Determine the nutrient type based on the name
            if ('cal' in name_lower and 'mag' in name_lower) or ('calmag' in name_lower):
                product.nutrient_type = 'calmag'
            elif 'micro' in name_lower:
                product.nutrient_type = 'micro'
            elif ('grow' in name_lower) or ('gro' in name_lower) or ('veg' in name_lower):
                product.nutrient_type = 'grow'
            elif ('bloom' in name_lower) or ('flower' in name_lower):
                product.nutrient_type = 'bloom'
            else:
                product.nutrient_type = 'other'
            
            updates += 1
        
        # Commit changes to database
        if updates > 0:
            db.session.commit()
            print(f"Updated nutrient_type for {updates} products.")
        else:
            print("No products needed updating.")

if __name__ == "__main__":
    migrate_nutrient_types() 