from app import db

class NutrientBrand(db.Model):
    __tablename__ = 'nutrient_brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=True)
    
    # Relationship
    products = db.relationship('NutrientProduct', backref='brand', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<NutrientBrand {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'products': [product.to_dict() for product in self.products]
        }
    
    @staticmethod
    def initialize_defaults():
        """Set up default nutrient brands if none exist"""
        if NutrientBrand.query.count() == 0:
            # Add common hydroponic nutrient brands
            default_brands = [
                {
                    'name': 'General Hydroponics',
                    'description': 'One of the most popular hydroponic nutrient brands',
                    'products': [
                        {'name': 'Flora Gro', 'nitrogen_pct': 3.0, 'phosphorus_pct': 1.0, 'potassium_pct': 6.0},
                        {'name': 'Flora Micro', 'nitrogen_pct': 5.0, 'phosphorus_pct': 0.0, 'potassium_pct': 1.0},
                        {'name': 'Flora Bloom', 'nitrogen_pct': 0.0, 'phosphorus_pct': 5.0, 'potassium_pct': 4.0},
                        {'name': 'CALiMAGic', 'nitrogen_pct': 2.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0},
                        {'name': 'pH Up', 'nitrogen_pct': 0.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0},
                        {'name': 'pH Down', 'nitrogen_pct': 0.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0}
                    ]
                },
                {
                    'name': 'Advanced Nutrients',
                    'description': 'Premium hydroponic nutrients for serious growers',
                    'products': [
                        {'name': 'pH Perfect Grow', 'nitrogen_pct': 3.0, 'phosphorus_pct': 1.0, 'potassium_pct': 4.0},
                        {'name': 'pH Perfect Micro', 'nitrogen_pct': 5.0, 'phosphorus_pct': 0.0, 'potassium_pct': 1.0},
                        {'name': 'pH Perfect Bloom', 'nitrogen_pct': 0.0, 'phosphorus_pct': 5.0, 'potassium_pct': 4.0},
                        {'name': 'CalMag Xtra', 'nitrogen_pct': 4.0, 'phosphorus_pct': 0.0, 'potassium_pct': 0.0}
                    ]
                },
                {
                    'name': 'Fox Farm',
                    'description': 'Premium plant nutrients and growing mediums',
                    'products': [
                        {'name': 'Grow Big Hydro', 'nitrogen_pct': 3.0, 'phosphorus_pct': 2.0, 'potassium_pct': 6.0},
                        {'name': 'Tiger Bloom', 'nitrogen_pct': 2.0, 'phosphorus_pct': 8.0, 'potassium_pct': 4.0},
                        {'name': 'Big Bloom', 'nitrogen_pct': 0.01, 'phosphorus_pct': 0.3, 'potassium_pct': 0.7}
                    ]
                },
                {
                    'name': 'Custom',
                    'description': 'User-defined custom nutrients',
                    'products': []
                }
            ]
            
            for brand_data in default_brands:
                brand = NutrientBrand(
                    name=brand_data['name'],
                    description=brand_data['description']
                )
                
                for product_data in brand_data['products']:
                    product = NutrientProduct(
                        name=product_data['name'],
                        nitrogen_pct=product_data['nitrogen_pct'],
                        phosphorus_pct=product_data['phosphorus_pct'],
                        potassium_pct=product_data['potassium_pct']
                    )
                    brand.products.append(product)
                
                db.session.add(brand)
                
            db.session.commit()

class NutrientProduct(db.Model):
    __tablename__ = 'nutrient_products'
    
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('nutrient_brands.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    nitrogen_pct = db.Column(db.Float, nullable=True)  # N percentage
    phosphorus_pct = db.Column(db.Float, nullable=True)  # P percentage
    potassium_pct = db.Column(db.Float, nullable=True)  # K percentage
    
    def __repr__(self):
        return f'<NutrientProduct {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'brand_id': self.brand_id,
            'name': self.name,
            'description': self.description,
            'nitrogen_pct': self.nitrogen_pct,
            'phosphorus_pct': self.phosphorus_pct,
            'potassium_pct': self.potassium_pct,
            'npk_label': f"{self.nitrogen_pct}-{self.phosphorus_pct}-{self.potassium_pct}" if all(v is not None for v in [self.nitrogen_pct, self.phosphorus_pct, self.potassium_pct]) else None
        } 