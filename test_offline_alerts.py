"""
Test script to manually trigger offline alerts.
"""
from core.database import get_db
from models.device import Device, DeviceStatus
from services.alert_service import check_device_offline

def test_offline_alerts():
    """Manually check and generate offline alerts."""
    print("=" * 70)
    print("Testing Offline Alert Generation")
    print("=" * 70)
    
    db = next(get_db())
    
    # Get all devices
    devices = db.query(Device).all()
    
    print(f"\n📱 Checking {len(devices)} devices...\n")
    
    offline_count = 0
    maintenance_count = 0
    
    for device in devices:
        if device.status == DeviceStatus.OFFLINE:
            offline_count += 1
            print(f"🔴 OFFLINE: {device.name} (ID: {device.id})")
            # Manually trigger alert check
            alert = check_device_offline(db, device)
            if alert:
                print(f"   ✅ Alert generated/updated")
            else:
                print(f"   ⚠️  No alert generated (may already exist)")
        
        elif device.status == DeviceStatus.MAINTENANCE:
            maintenance_count += 1
            print(f"🟡 MAINTENANCE: {device.name} (ID: {device.id})")
            # Manually trigger alert check
            alert = check_device_offline(db, device)
            if alert:
                print(f"   ✅ Alert generated/updated")
            else:
                print(f"   ⚠️  No alert generated (may already exist)")
    
    print(f"\n📊 Summary:")
    print(f"   - Offline devices: {offline_count}")
    print(f"   - Maintenance devices: {maintenance_count}")
    
    # Check alerts now
    from models.alert import Alert, AlertType, AlertStatus
    from sqlalchemy import and_
    
    offline_alerts = db.query(Alert).filter(
        and_(
            Alert.alert_type == AlertType.DEVICE_OFFLINE,
            Alert.status == AlertStatus.ACTIVE
        )
    ).all()
    
    print(f"\n🚨 Active Offline/Maintenance Alerts: {len(offline_alerts)}")
    for alert in offline_alerts:
        device = db.query(Device).filter(Device.id == alert.device_id).first()
        print(f"   - {device.name if device else 'Unknown'}: {alert.message}")

if __name__ == "__main__":
    try:
        test_offline_alerts()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

