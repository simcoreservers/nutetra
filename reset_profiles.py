from app import create_app, db
from app.models.settings import Settings

def reset_all_profiles():
    """Reset all plant profiles to their defaults and reconfigure nutrient components"""
    app = create_app()
    with app.app_context():
        print("Resetting all plant profiles to defaults")
        
        # Force reset profiles to defaults
        Settings.initialize_defaults(force_reset=True)
        
        # Now run auto-configuration
        result = Settings.auto_configure_nutrient_components()
        
        print(f"Auto-configuration complete. Found {result.get('pumps_found', 0)} nutrient pumps.")
        
        # Print the nutrient components for the General profile
        plant_profiles = Settings.get('plant_profiles', {})
        if 'general' in plant_profiles:
            general = plant_profiles['general']
            components = general.get('nutrient_components', [])
            
            print(f"\nGeneral profile has {len(components)} nutrient components:")
            for i, comp in enumerate(components):
                print(f"{i+1}. {comp.get('pump_name')} - Type: {comp.get('nutrient_type')} - Order: {comp.get('dosing_order')}")
                print(f"   Dosing: {comp.get('dosing_ml_per_liter', 'N/A')} ml/L ({comp.get('dosing_ml_per_gallon', 'N/A')} ml/gal)")
        
        print("\nReset complete. Restart your Flask server and refresh the browser.")

if __name__ == "__main__":
    reset_all_profiles() 