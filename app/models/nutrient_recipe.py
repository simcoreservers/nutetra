from app import db
from datetime import datetime

class NutrientRecipe(db.Model):
    __tablename__ = 'nutrient_recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Recipe components (relationships)
    components = db.relationship('RecipeComponent', backref='recipe', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<NutrientRecipe {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'components': [component.to_dict() for component in self.components]
        }
    
    @staticmethod
    def get_active_recipes():
        """Get all active recipes"""
        return NutrientRecipe.query.filter_by(is_active=True).all()
    
    @staticmethod
    def initialize_default():
        """Create a default recipe if none exists"""
        if NutrientRecipe.query.count() == 0:
            default_recipe = NutrientRecipe(
                name="Basic Hydroponic Nutrient Solution",
                description="Standard A/B nutrient solution for leafy greens",
                is_active=True
            )
            
            db.session.add(default_recipe)
            db.session.flush()  # Flush to get the ID
            
            # Find the default nutrient pumps
            from app.models.pump import Pump
            nutrient_a = Pump.query.filter_by(type='nutrient_a').first()
            nutrient_b = Pump.query.filter_by(type='nutrient_b').first()
            
            # Add components if pumps exist
            if nutrient_a:
                comp_a = RecipeComponent(
                    recipe_id=default_recipe.id,
                    pump_id=nutrient_a.id,
                    ratio=1.0,
                    name="Part A"
                )
                db.session.add(comp_a)
                
            if nutrient_b:
                comp_b = RecipeComponent(
                    recipe_id=default_recipe.id,
                    pump_id=nutrient_b.id,
                    ratio=1.0,
                    name="Part B"
                )
                db.session.add(comp_b)
                
            db.session.commit()


class RecipeComponent(db.Model):
    __tablename__ = 'recipe_components'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('nutrient_recipes.id'), nullable=False)
    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id'), nullable=False)
    ratio = db.Column(db.Float, nullable=False, default=1.0)  # Relative ratio in the recipe
    name = db.Column(db.String(50))  # Optional name for the component
    
    # Relationship to pump
    pump = db.relationship('Pump')
    
    def __repr__(self):
        return f'<RecipeComponent {self.id}: {self.name or "Unnamed"} (ratio: {self.ratio})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'pump_id': self.pump_id,
            'pump_name': self.pump.name if self.pump else 'Unknown',
            'ratio': self.ratio,
            'name': self.name
        } 