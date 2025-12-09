"""
Check actual alerts in database.
"""
from core.database import get_db
from models.alert import Alert, AlertType, AlertStatus
from models.device import Device

def check_actual_alerts():
    """Check what alerts actually exist in database."""
    print("=" * 70)
    print("Actual Alerts in Database")
    print("=" * 70)
    
    db = next(get_db())
    
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    
    print(f"\n📊 Total Alerts: {len(alerts)}")
    
    active_alerts = [a for a in alerts if a.status.value == "active"]
    print(f"🚨 Active Alerts: {len(active_alerts)}")
    
    if active_alerts:
        print("\n" + "=" * 70)
        print("Active Alerts Details:")
        print("=" * 70)
        
        for i, alert in enumerate(active_alerts, 1):
            device = db.query(Device).filter(Device.id == alert.device_id).first()
            device_name = device.name if device else f"Device {alert.device_id}"
            
            print(f"\n{i}. {alert.alert_type.value.replace('_', ' ').title()}")
            print(f"   Device: {device_name}")
            print(f"   Message: {alert.message}")
            print(f"   Status: {alert.status.value.upper()}")
            print(f"   Severity: {alert.severity}")
            if alert.water_level_cm:
                print(f"   Water Level: {alert.water_level_cm:.1f} cm")
            if alert.threshold_cm:
                print(f"   Threshold: {alert.threshold_cm} cm")
            print(f"   Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Count by type
    type_counts = {}
    for alert in active_alerts:
        alert_type = alert.alert_type.value
        type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
    
    print("\n" + "=" * 70)
    print("Alert Summary by Type:")
    print("=" * 70)
    for alert_type, count in type_counts.items():
        print(f"   {alert_type.replace('_', ' ').title()}: {count}")
    
    # Check for expected alerts
    print("\n" + "=" * 70)
    print("Expected vs Actual:")
    print("=" * 70)
    print(f"   Expected High Water Level Alerts: 4 (from water level overrides)")
    print(f"   Actual High Water Level Alerts: {type_counts.get('high_water_level', 0)}")
    print(f"   Expected Offline Alerts: 2")
    print(f"   Actual Offline Alerts: {type_counts.get('device_offline', 0)}")
    print(f"   Expected Rate of Rise Alerts: 2")
    print(f"   Actual Rate of Rise Alerts: {type_counts.get('rate_of_rise', 0)}")

if __name__ == "__main__":
    try:
        check_actual_alerts()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

