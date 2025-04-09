from app import create_app, db
from app.models.settings import Settings
from app.models.pump import Pump
import json

def force_update_profiles():
    """Force update all profiles with the new dosing sequence"""
    app = create_app()
    with app.app_context():
        # Get current profiles
        plant_profiles = Settings.get('plant_profiles', {})
        print(f"Found {len(plant_profiles)} plant profiles")
        
        # Get nutrient pumps
        nutrient_pumps = Pump.query.filter(
            Pump.type == 'nutrient'
        ).all()
        print(f"Found {len(nutrient_pumps)} nutrient pumps")
        
        # Perform manual classification - print what we found
        for pump in nutrient_pumps:
            name = pump.nutrient_name.lower() if pump.nutrient_name else pump.name.lower()
            nutrient_type = None
            if any(term in name for term in ['cal', 'mag', 'calcium', 'magnesium']):
                nutrient_type = 'calmag'
            elif any(term in name for term in ['micro', 'trace']):
                nutrient_type = 'micro'
            elif any(term in name for term in ['grow', 'veg', 'vegetative']):
                nutrient_type = 'grow'
            elif any(term in name for term in ['bloom', 'flower', 'fruit']):
                nutrient_type = 'bloom'
            else:
                nutrient_type = 'grow'  # Default
            
            print(f"Pump {pump.id}: {pump.name} - Type: {nutrient_type}")
            
        # Define dosing order
        type_order = {
            'calmag': 1,  # Cal-mag supplements go first
            'micro': 2,   # Micro/trace nutrients second
            'grow': 3,    # Grow nutrients third
            'bloom': 4    # Bloom nutrients last
        }
        
        # Reset all profiles to force update
        for profile_id, profile in plant_profiles.items():
            if not profile.get('custom', True):  # Only update default profiles
                # Force profiles to rebuild components
                profile['nutrient_components'] = []
        
        # Save profiles - this will force a rebuild
        Settings.set('plant_profiles', plant_profiles)
        print("Profiles reset - they will be rebuilt on next access")
        
        # Now manually run the auto-configure
        result = Settings.auto_configure_nutrient_components()
        print(f"Auto-configuration result: {json.dumps(result, indent=2)}")
        
        # Get updated profiles to show what we have
        updated_profiles = Settings.get('plant_profiles', {})
        
        # Print first profile components to verify order
        if updated_profiles:
            print("\nVerifying first profile components:")
            first_profile_id = next(iter(updated_profiles))
            first_profile = updated_profiles[first_profile_id]
            
            for i, component in enumerate(first_profile.get('nutrient_components', [])):
                print(f"{i+1}. {component.get('pump_name')} - Type: {component.get('nutrient_type')} - Order: {component.get('dosing_order')}")

if __name__ == '__main__':
    force_update_profiles() 