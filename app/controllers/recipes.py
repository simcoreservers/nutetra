from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.nutrient_recipe import NutrientRecipe, RecipeComponent
from app.models.pump import Pump
from app.models.settings import Settings
from app import db

# Create a blueprint
recipes_bp = Blueprint('recipes', __name__)

@recipes_bp.route('/')
def index():
    """Show recipe management page"""
    # Get all recipes
    recipes = NutrientRecipe.query.all()
    
    # Get active recipe
    active_recipe_id = Settings.get('active_recipe_id')
    active_recipe = None
    
    if active_recipe_id:
        active_recipe = NutrientRecipe.query.get(active_recipe_id)
    
    return render_template(
        'recipes/index.html',
        recipes=recipes,
        active_recipe=active_recipe
    )

@recipes_bp.route('/add', methods=['GET', 'POST'])
def add_recipe():
    """Add a new nutrient recipe"""
    if request.method == 'POST':
        # Get recipe details from form
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Validate input
        if not name:
            flash('Recipe name is required', 'error')
            return redirect(url_for('recipes.add_recipe'))
        
        # Create the new recipe
        new_recipe = NutrientRecipe(
            name=name,
            description=description,
            is_active=True
        )
        
        # Save to database
        db.session.add(new_recipe)
        db.session.commit()
        
        flash(f'Recipe "{name}" created successfully', 'success')
        return redirect(url_for('recipes.edit_recipe', recipe_id=new_recipe.id))
    
    # For GET requests, show the add recipe form
    return render_template('recipes/add_recipe.html')

@recipes_bp.route('/edit/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    """Edit an existing recipe"""
    # Get the recipe
    recipe = NutrientRecipe.query.get_or_404(recipe_id)
    
    if request.method == 'POST':
        # Get recipe details from form
        name = request.form.get('name')
        description = request.form.get('description')
        is_active = 'is_active' in request.form
        
        # Validate input
        if not name:
            flash('Recipe name is required', 'error')
            return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))
        
        # Update the recipe
        recipe.name = name
        recipe.description = description
        recipe.is_active = is_active
        
        # Save to database
        db.session.commit()
        
        flash(f'Recipe "{name}" updated successfully', 'success')
        return redirect(url_for('recipes.index'))
    
    # Get all available nutrient pumps
    nutrient_pumps = Pump.query.filter(
        Pump.type.in_(['nutrient_a', 'nutrient_b', 'nutrient_c', 'custom']),
        Pump.enabled == True
    ).all()
    
    # For GET requests, show the edit recipe form
    return render_template(
        'recipes/edit_recipe.html',
        recipe=recipe,
        nutrient_pumps=nutrient_pumps
    )

@recipes_bp.route('/delete/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    """Delete a recipe"""
    recipe = NutrientRecipe.query.get_or_404(recipe_id)
    
    # Check if this is the active recipe
    active_recipe_id = Settings.get('active_recipe_id')
    if active_recipe_id and int(active_recipe_id) == recipe_id:
        flash('Cannot delete the active recipe', 'error')
        return redirect(url_for('recipes.index'))
    
    # Delete the recipe
    recipe_name = recipe.name
    db.session.delete(recipe)
    db.session.commit()
    
    flash(f'Recipe "{recipe_name}" deleted successfully', 'success')
    return redirect(url_for('recipes.index'))

@recipes_bp.route('/component/add/<int:recipe_id>', methods=['POST'])
def add_component(recipe_id):
    """Add a component to a recipe"""
    recipe = NutrientRecipe.query.get_or_404(recipe_id)
    
    # Get component details from form
    pump_id = request.form.get('pump_id', type=int)
    name = request.form.get('component_name')
    ratio = request.form.get('ratio', type=float, default=1.0)
    
    # Validate input
    if not pump_id:
        flash('Pump selection is required', 'error')
        return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))
    
    # Check if pump exists
    pump = Pump.query.get(pump_id)
    if not pump:
        flash('Selected pump does not exist', 'error')
        return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))
    
    # Check if pump is already in the recipe
    existing = RecipeComponent.query.filter_by(
        recipe_id=recipe_id,
        pump_id=pump_id
    ).first()
    
    if existing:
        flash(f'Pump "{pump.name}" is already in this recipe', 'error')
        return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))
    
    # Create the new component
    new_component = RecipeComponent(
        recipe_id=recipe_id,
        pump_id=pump_id,
        name=name or pump.name,
        ratio=ratio
    )
    
    # Save to database
    db.session.add(new_component)
    db.session.commit()
    
    flash(f'Component "{new_component.name}" added to recipe', 'success')
    return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))

@recipes_bp.route('/component/edit/<int:component_id>', methods=['POST'])
def edit_component(component_id):
    """Edit a recipe component"""
    component = RecipeComponent.query.get_or_404(component_id)
    
    # Get component details from form
    name = request.form.get('component_name')
    ratio = request.form.get('ratio', type=float)
    
    # Validate input
    if ratio is None or ratio <= 0:
        flash('Ratio must be greater than 0', 'error')
        return redirect(url_for('recipes.edit_recipe', recipe_id=component.recipe_id))
    
    # Update the component
    component.name = name
    component.ratio = ratio
    
    # Save to database
    db.session.commit()
    
    flash(f'Component "{component.name}" updated successfully', 'success')
    return redirect(url_for('recipes.edit_recipe', recipe_id=component.recipe_id))

@recipes_bp.route('/component/delete/<int:component_id>', methods=['POST'])
def delete_component(component_id):
    """Delete a recipe component"""
    component = RecipeComponent.query.get_or_404(component_id)
    recipe_id = component.recipe_id
    
    # Delete the component
    component_name = component.name
    db.session.delete(component)
    db.session.commit()
    
    flash(f'Component "{component_name}" removed from recipe', 'success')
    return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))

@recipes_bp.route('/set-active/<int:recipe_id>', methods=['POST'])
def set_active_recipe(recipe_id):
    """Set a recipe as the active one for dosing"""
    recipe = NutrientRecipe.query.get_or_404(recipe_id)
    
    # Ensure the recipe has components
    if not recipe.components:
        flash('Cannot activate a recipe with no components', 'error')
        return redirect(url_for('recipes.index'))
    
    # Set as active
    Settings.set('active_recipe_id', recipe_id)
    
    flash(f'Recipe "{recipe.name}" set as active for nutrient dosing', 'success')
    return redirect(url_for('recipes.index')) 