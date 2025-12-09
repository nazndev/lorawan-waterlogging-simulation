"""
Cleanup script to delete readings and alerts, but keep users and devices.
Useful for resetting simulation data while keeping device configuration.
"""
import logging
import sys
from core.database import get_db, init_db
from models.reading import Reading
from models.alert import Alert
from models.device import Device
from models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_simulation_data():
    """Delete all readings and alerts, but keep users and devices."""
    print("🧹 Starting data cleanup...")
    
    try:
        db = next(get_db())
        
        # Count records before deletion
        reading_count = db.query(Reading).count()
        alert_count = db.query(Alert).count()
        device_count = db.query(Device).count()
        user_count = db.query(User).count()
        
        print(f"\n📊 Current Data:")
        print(f"   - Users: {user_count}")
        print(f"   - Devices: {device_count}")
        print(f"   - Readings: {reading_count}")
        print(f"   - Alerts: {alert_count}")
        
        # Delete all readings
        if reading_count > 0:
            print(f"\n🗑️  Deleting {reading_count} readings...")
            db.query(Reading).delete()
            print("   ✅ Readings deleted")
        else:
            print("\n   ℹ️  No readings to delete")
        
        # Delete all alerts
        if alert_count > 0:
            print(f"\n🗑️  Deleting {alert_count} alerts...")
            db.query(Alert).delete()
            print("   ✅ Alerts deleted")
        else:
            print("\n   ℹ️  No alerts to delete")
        
        # Reset device status and last_seen (to make devices "fresh" for new simulation)
        print(f"\n🔄 Resetting device status...")
        from models.device import DeviceStatus
        import sys
        
        devices = db.query(Device).all()
        reset_params = "--reset-params" in sys.argv or "-r" in sys.argv
        
        if reset_params:
            from simulation.traffic_generator import calculate_distance_to_gateway
            import random
        
        for device in devices:
            device.last_seen = None
            device.status = DeviceStatus.ONLINE  # Reset all devices to ONLINE
            
            # Optionally reset device parameters to default values
            if reset_params:
                # Recalculate SF based on distance (same logic as create_demo_devices)
                distance_km = calculate_distance_to_gateway(device.latitude, device.longitude)
                if distance_km < 5:
                    device.spreading_factor = random.choice([7, 8, 9])
                elif distance_km < 15:
                    device.spreading_factor = random.choice([9, 10, 11])
                else:
                    device.spreading_factor = random.choice([10, 11, 12])
                
                # Reset TX power to random default
                device.tx_power_dbm = random.choice([2, 5, 8, 11, 14])
                
                # Reset battery level to random default
                device.battery_level = random.uniform(60.0, 100.0)
        
        if reset_params:
            print(f"   ✅ Reset last_seen, status, SF, TX power, and battery for {len(devices)} devices")
        else:
            print(f"   ✅ Reset last_seen and status to ONLINE for {len(devices)} devices")
            print(f"   ℹ️  Device parameters (SF, TX power, battery) were preserved")
            print(f"   💡 Use --reset-params flag to also reset device parameters to defaults")
        
        # Commit changes
        db.commit()
        
        # Verify deletion
        remaining_readings = db.query(Reading).count()
        remaining_alerts = db.query(Alert).count()
        
        print(f"\n✅ Cleanup Complete!")
        print(f"\n📊 Remaining Data:")
        print(f"   - Users: {user_count} (preserved)")
        print(f"   - Devices: {device_count} (preserved)")
        print(f"   - Readings: {remaining_readings} (deleted)")
        print(f"   - Alerts: {remaining_alerts} (deleted)")
        
        print(f"\n💡 You can now run the simulation fresh with existing devices.")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Data Cleanup Script")
    print("=" * 60)
    print("\nThis script will:")
    print("  ✅ Keep: Users and Devices")
    print("  🗑️  Delete: Readings and Alerts")
    print("  🔄 Reset: Device last_seen timestamps and status to ONLINE")
    
    reset_params = "--reset-params" in sys.argv or "-r" in sys.argv
    if reset_params:
        print("  🔄 Reset: Device parameters (SF, TX power, battery) to default values")
    else:
        print("  ✅ Preserve: Device parameters (SF, TX power, battery)")
        print("  💡 Tip: Use --reset-params flag to also reset device parameters")
    
    print("\n" + "=" * 60)
    
    # Check if --yes flag is provided for non-interactive mode
    if "--yes" in sys.argv or "-y" in sys.argv:
        print("\n🚀 Running in non-interactive mode...\n")
        cleanup_simulation_data()
    else:
        try:
            response = input("\n⚠️  Continue? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                cleanup_simulation_data()
            else:
                print("\n❌ Cleanup cancelled.")
        except EOFError:
            # If running non-interactively, just proceed
            print("\n🚀 Running in non-interactive mode...\n")
            cleanup_simulation_data()

