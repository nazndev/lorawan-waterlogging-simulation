"""
Script to set up test scenario with specific device configurations.
"""
from core.database import get_db
from models.device import Device, DeviceStatus
from simulation.simulator_runner import SimulatorRunner

def setup_test_scenario():
    """Set up devices with specific test configurations."""
    print("=" * 70)
    print("Setting Up Test Scenario")
    print("=" * 70)
    
    db = next(get_db())
    devices = db.query(Device).all()
    
    if len(devices) < 6:
        print(f"❌ Need at least 6 devices, but only {len(devices)} found.")
        print("   Run `python init_db.py` to create more devices.")
        return
    
    print(f"\n📱 Found {len(devices)} devices")
    print("\n🔧 Configuring devices for test scenario...\n")
    
    # Device 1: Set to OFFLINE
    device1 = devices[0]
    device1.status = DeviceStatus.OFFLINE
    device1.last_seen = None
    print(f"✅ Device 1: {device1.name}")
    print(f"   Status: OFFLINE")
    print(f"   Last Seen: None")
    
    # Device 2: Set to MAINTENANCE
    device2 = devices[1]
    device2.status = DeviceStatus.MAINTENANCE
    print(f"\n✅ Device 2: {device2.name}")
    print(f"   Status: MAINTENANCE")
    
    # Device 3: Set water level override to > 50 cm (for alert)
    device3 = devices[2]
    # Note: Water level overrides are stored in session state, not database
    # So we'll set a high initial water level by modifying the device's last level
    # Or user can set it manually in UI
    print(f"\n✅ Device 3: {device3.name}")
    print(f"   Water Level Override: 60 cm (will trigger alert)")
    print(f"   💡 Set this in UI: Simulation Control → Manual Water Level Control")
    print(f"      Select '{device3.name}' and set to 60 cm")
    
    # Device 4: Set battery level < 20%
    device4 = devices[3]
    device4.battery_level = 15.0
    print(f"\n✅ Device 4: {device4.name}")
    print(f"   Battery Level: {device4.battery_level}%")
    
    # Device 5: Set spreading factor to 11
    device5 = devices[4]
    device5.spreading_factor = 11
    print(f"\n✅ Device 5: {device5.name}")
    print(f"   Spreading Factor: SF{device5.spreading_factor}")
    print(f"   (Higher SF = longer range, more airtime)")
    
    # Device 6: Set TX power to 2 dBm
    device6 = devices[5]
    device6.tx_power_dbm = 2.0
    print(f"\n✅ Device 6: {device6.name}")
    print(f"   TX Power: {device6.tx_power_dbm} dBm")
    print(f"   (Lower power = weaker signal, shorter range)")
    
    # Commit changes
    db.commit()
    
    print("\n" + "=" * 70)
    print("✅ Test Scenario Setup Complete!")
    print("=" * 70)
    print("\n📋 Summary:")
    print(f"   - Device 1 ({device1.name}): OFFLINE")
    print(f"   - Device 2 ({device2.name}): MAINTENANCE")
    print(f"   - Device 3 ({device3.name}): Set water level to 60 cm in UI")
    print(f"   - Device 4 ({device4.name}): Battery 15%")
    print(f"   - Device 5 ({device5.name}): SF11")
    print(f"   - Device 6 ({device6.name}): TX Power 2 dBm")
    
    print("\n💡 Next Steps:")
    print("   1. Go to Simulation Control page")
    print("   2. In 'Manual Water Level Control', set Device 3 to 60 cm")
    print("   3. Start simulation")
    print("   4. Check Dashboard/Alerts page for generated alerts")
    print("   5. Check Devices page to see all configurations")
    
    print("\n🔍 Expected Results:")
    print("   - Device 1: Should generate OFFLINE alert")
    print("   - Device 3: Should generate HIGH_WATER_LEVEL alert (if water level > threshold)")
    print("   - Device 5: Higher SF = better range but more collisions")
    print("   - Device 6: Lower TX power = weaker signal, may have packet failures")

if __name__ == "__main__":
    try:
        setup_test_scenario()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

