from app import db, create_app
from app.models.nutrient import NutrientBrand, NutrientProduct
from app.models.settings import Settings

# Create app context
app = create_app()
with app.app_context():
    # Find Flora Gro product
    flora_gro = NutrientProduct.query.join(NutrientBrand).filter(
        NutrientBrand.name == 'General Hydroponics',
        NutrientProduct.name == 'Flora Gro'
    ).first()
    
    if flora_gro:
        old_type = flora_gro.nutrient_type or 'None'
        print(f"Found Flora Gro with current type: {old_type}")
        
        # Update to "grow" type
        flora_gro.nutrient_type = 'grow'
        db.session.commit()
        print(f"Updated Flora Gro nutrient type from '{old_type}' to 'grow'")
        
        # Force update of all profiles
        update_result = Settings.auto_configure_nutrient_components(forced=True)
        print(f"Profile update result: {update_result}")
    else:
        print("Flora Gro product not found. Check your database.")
        
        # List available products for debugging
        print("\nAvailable General Hydroponics products:")
        gh_products = NutrientProduct.query.join(NutrientBrand).filter(
            NutrientBrand.name == 'General Hydroponics'
        ).all()
        
        if gh_products:
            for product in gh_products:
                print(f" - {product.name} (type: {product.nutrient_type})")
        else:
            print("No General Hydroponics products found.")
            
        # List all brands
        print("\nAvailable brands:")
        brands = NutrientBrand.query.all()
        for brand in brands:
            print(f" - {brand.name}")

print("Script completed.") 