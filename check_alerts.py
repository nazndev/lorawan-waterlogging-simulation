"""
Script to check how many alerts should be generated based on current database data.
"""
import sys
from core.database import get_db
from models.reading import Reading
from models.device import Device
from models.alert import Alert, AlertType, AlertStatus
from services.alert_service import check_water_level_alerts, check_rate_of_rise, check_device_offline
from core.config import APP_CONFIG
import core.config as config_module
from datetime import datetime, timedelta
from sqlalchemy import desc

def check_expected_alerts():
    """Check database and calculate expected alerts."""
    print("=" * 70)
    print("Alert Generation Analysis")
    print("=" * 70)
    
    db = next(get_db())
    
    # Get current thresholds
    water_threshold = config_module.APP_CONFIG["water_level_threshold_cm"]
    rate_threshold = config_module.APP_CONFIG["rate_of_rise_threshold_cm_per_hour"]
    offline_threshold_min = config_module.APP_CONFIG["device_offline_threshold_minutes"]
    
    print(f"\n📊 Current Alert Thresholds:")
    print(f"   - Water Level Threshold: {water_threshold} cm")
    print(f"   - Rate of Rise Threshold: {rate_threshold} cm/hour")
    print(f"   - Device Offline Threshold: {offline_threshold_min} minutes")
    
    # Get all devices
    devices = db.query(Device).all()
    print(f"\n📱 Devices: {len(devices)} total")
    
    device_status_counts = {}
    for device in devices:
        status = device.status.value
        device_status_counts[status] = device_status_counts.get(status, 0) + 1
    
    for status, count in device_status_counts.items():
        print(f"   - {status.upper()}: {count}")
    
    # Get all readings
    readings = db.query(Reading).order_by(desc(Reading.timestamp)).all()
    print(f"\n📈 Readings: {len(readings)} total")
    
    if not readings:
        print("   ⚠️  No readings found in database!")
        print("\n💡 To generate alerts:")
        print("   1. Start the simulation (it will generate readings for all ONLINE devices)")
        print("   2. Set water levels above threshold using 'Manual Water Level Control'")
        print("   3. Or wait for natural water level increases")
        print("\n📊 Expected behavior when simulation runs:")
        print(f"   - {len(devices)} devices will generate readings")
        print(f"   - Alerts will be created if water level > {water_threshold} cm")
        print(f"   - Alerts will be created if rate of rise > {rate_threshold} cm/hour")
        print(f"   - Alerts will be created if device offline > {offline_threshold_min} minutes")
        return
    
    # Get latest reading per device
    latest_readings = {}
    for reading in readings:
        if reading.device_id not in latest_readings:
            latest_readings[reading.device_id] = reading
    
    print(f"   - Devices with readings: {len(latest_readings)}")
    
    # Check water level alerts
    print(f"\n💧 High Water Level Alerts:")
    high_water_count = 0
    high_water_devices = []
    
    for device_id, reading in latest_readings.items():
        if reading.water_level_cm > water_threshold:
            high_water_count += 1
            device = next((d for d in devices if d.id == device_id), None)
            device_name = device.name if device else f"Device {device_id}"
            high_water_devices.append({
                "device": device_name,
                "water_level": reading.water_level_cm,
                "threshold": water_threshold
            })
            print(f"   ✅ {device_name}: {reading.water_level_cm:.1f} cm > {water_threshold} cm")
    
    if high_water_count == 0:
        print(f"   ℹ️  No devices exceed water level threshold")
    
    # Check rate of rise alerts
    print(f"\n📈 Rate of Rise Alerts:")
    rate_rise_count = 0
    rate_rise_devices = []
    
    for device_id, reading in latest_readings.items():
        device = next((d for d in devices if d.id == device_id), None)
        if device:
            # Get readings from last hour
            one_hour_ago = reading.timestamp - timedelta(hours=1)
            device_readings = [r for r in readings 
                             if r.device_id == device_id and r.timestamp >= one_hour_ago]
            
            if len(device_readings) >= 2:
                # Calculate rate of rise
                oldest = min(device_readings, key=lambda r: r.timestamp)
                newest = max(device_readings, key=lambda r: r.timestamp)
                
                time_diff_hours = (newest.timestamp - oldest.timestamp).total_seconds() / 3600
                if time_diff_hours > 0:
                    level_diff = newest.water_level_cm - oldest.water_level_cm
                    rate = level_diff / time_diff_hours
                    
                    if rate > rate_threshold:
                        rate_rise_count += 1
                        rate_rise_devices.append({
                            "device": device.name,
                            "rate": rate,
                            "threshold": rate_threshold
                        })
                        print(f"   ✅ {device.name}: {rate:.1f} cm/hour > {rate_threshold} cm/hour")
    
    if rate_rise_count == 0:
        print(f"   ℹ️  No devices exceed rate of rise threshold")
    
    # Check offline device alerts
    print(f"\n📴 Device Offline Alerts:")
    offline_count = 0
    offline_devices = []
    
    offline_threshold = timedelta(minutes=offline_threshold_min)
    now = datetime.now(reading.timestamp.tzinfo) if readings else datetime.now()
    
    for device in devices:
        if device.status.value == "offline":
            offline_count += 1
            offline_devices.append({
                "device": device.name,
                "last_seen": device.last_seen
            })
            print(f"   ✅ {device.name}: Status is OFFLINE")
        elif device.last_seen:
            time_since = now - device.last_seen
            if time_since > offline_threshold:
                offline_count += 1
                offline_devices.append({
                    "device": device.name,
                    "last_seen": device.last_seen,
                    "minutes_ago": time_since.total_seconds() / 60
                })
                print(f"   ✅ {device.name}: Last seen {time_since.total_seconds()/60:.1f} minutes ago")
    
    if offline_count == 0:
        print(f"   ℹ️  No offline devices")
    
    # Get existing alerts
    existing_alerts = db.query(Alert).all()
    active_alerts = [a for a in existing_alerts if a.status.value == "active"]
    
    print(f"\n🚨 Existing Alerts in Database:")
    print(f"   - Total Alerts: {len(existing_alerts)}")
    print(f"   - Active Alerts: {len(active_alerts)}")
    
    alert_type_counts = {}
    for alert in active_alerts:
        alert_type = alert.alert_type.value
        alert_type_counts[alert_type] = alert_type_counts.get(alert_type, 0) + 1
    
    for alert_type, count in alert_type_counts.items():
        print(f"   - {alert_type.replace('_', ' ').title()}: {count}")
    
    # Summary
    print(f"\n" + "=" * 70)
    print("📊 Expected Alert Summary:")
    print("=" * 70)
    print(f"   High Water Level Alerts: {high_water_count}")
    print(f"   Rate of Rise Alerts: {rate_rise_count}")
    print(f"   Device Offline Alerts: {offline_count}")
    print(f"   Total Expected Alerts: {high_water_count + rate_rise_count + offline_count}")
    print(f"\n   Currently Active Alerts: {len(active_alerts)}")
    
    if high_water_count + rate_rise_count + offline_count != len(active_alerts):
        print(f"\n   ⚠️  Mismatch detected!")
        print(f"   Expected: {high_water_count + rate_rise_count + offline_count}, Found: {len(active_alerts)}")
    else:
        print(f"\n   ✅ Alert count matches expected!")

if __name__ == "__main__":
    try:
        check_expected_alerts()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

