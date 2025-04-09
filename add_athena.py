from app import create_app, db
from app.models.nutrient import NutrientBrand, NutrientProduct

def add_athena():
    app = create_app()
    with app.app_context():
        # Check if Athena already exists
        athena = NutrientBrand.query.filter_by(name='Athena').first()
        if athena:
            print("Athena brand already exists in the database.")
            return
        
        # Create Athena brand
        athena = NutrientBrand(
            name='Athena',
            description='Professional-grade hydroponic nutrients for commercial growers'
        )
        db.session.add(athena)
        db.session.commit()
        
        # Add Athena products
        products = [
            {'name': 'Grow A', 'nitrogen_pct': 3.0, 'phosphorus_pct': 1.0, 'potassium_pct': 4.0},
            {'name': 'Grow B', 'nitrogen_pct': 1.0, 'phosphorus_pct': 0.0, 'potassium_pct': 1.0},
            {'name': 'Bloom A', 'nitrogen_pct': 1.0, 'phosphorus_pct': 4.0, 'potassium_pct': 5.0},
            {'name': 'Bloom B', 'nitrogen_pct': 1.0, 'phosphorus_pct': 0.0, 'potassium_pct': 1.0},
            {'name': 'Core', 'nitrogen_pct': 2.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0},
            {'name': 'Balance', 'nitrogen_pct': 0.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0},
            {'name': 'Stack', 'nitrogen_pct': 0.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0}
        ]
        
        for product_data in products:
            product = NutrientProduct(
                brand_id=athena.id,
                name=product_data['name'],
                nitrogen_pct=product_data['nitrogen_pct'],
                phosphorus_pct=product_data['phosphorus_pct'],
                potassium_pct=product_data['potassium_pct']
            )
            db.session.add(product)
        
        db.session.commit()
        print(f"Added Athena brand with {len(products)} products to the database.")

if __name__ == '__main__':
    add_athena() 