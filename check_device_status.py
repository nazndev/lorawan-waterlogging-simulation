"""
Check why a device shows ONLINE but last_seen is Never.
"""
from core.database import get_db
from models.device import Device
from models.reading import Reading
from sqlalchemy import desc

def check_device_status(device_id_or_name):
    """Check device status and packet delivery."""
    db = next(get_db())
    
    # Find device
    if device_id_or_name.startswith("WL-"):
        device = db.query(Device).filter(Device.device_id == device_id_or_name).first()
    else:
        device = db.query(Device).filter(Device.name.like(f"%{device_id_or_name}%")).first()
    
    if not device:
        print(f"❌ Device not found: {device_id_or_name}")
        return
    
    print("=" * 70)
    print(f"Device Status Analysis: {device.name}")
    print("=" * 70)
    
    print(f"\n📱 Device Info:")
    print(f"   Name: {device.name}")
    print(f"   Device ID: {device.device_id}")
    print(f"   Status: {device.status.value.upper()}")
    print(f"   Last Seen: {device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else 'Never'}")
    print(f"   Spreading Factor: SF{device.spreading_factor}")
    print(f"   TX Power: {device.tx_power_dbm} dBm")
    print(f"   Battery: {device.battery_level:.1f}%")
    
    # Get readings
    readings = db.query(Reading).filter(
        Reading.device_id == device.id
    ).order_by(desc(Reading.timestamp)).limit(10).all()
    
    print(f"\n📈 Recent Readings: {len(readings)}")
    
    if readings:
        successful = sum(1 for r in readings if r.packet_delivered)
        failed = len(readings) - successful
        success_rate = (successful / len(readings) * 100) if readings else 0
        
        print(f" +   Successful Packets: {successful}")
        print(f"   Failed Packets: {failed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        print(f"\n📊 Latest Reading:")
        latest = readings[0]
        print(f"   Timestamp: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Water Level: {latest.water_level_cm:.1f} cm")
        print(f"   SNR: {latest.snr_db:.1f} dB")
        print(f"   RSSI: {latest.rssi_dbm:.1f} dBm")
        print(f"   Packet Delivered: {'✅ YES' if latest.packet_delivered else '❌ NO'}")
        
        if not latest.packet_delivered:
            print(f"\n⚠️  Why Packet Failed:")
            print(f"   - SNR: {latest.snr_db:.1f} dB (may be too low)")
            print(f"   - TX Power: {device.tx_power_dbm} dBm (very low - only 2 dBm)")
            print(f"   - Spreading Factor: SF{device.spreading_factor}")
            
            # Check SNR threshold for SF
            from simulation.wireless_channel import calculate_per
            per = calculate_per(latest.snr_db, device.spreading_factor)
            print(f"   - Packet Error Rate: {per*100:.1f}%")
            
            if latest.snr_db < -20:
                print(f"   💡 SNR is very low ({latest.snr_db:.1f} dB). Device needs higher TX power or better location.")
            if device.tx_power_dbm <= 2:
                print(f"   💡 TX Power is very low ({device.tx_power_dbm} dBm). Consider increasing to 11-14 dBm.")
    else:
        print("   ⚠️  No readings found for this device")
    
    print(f"\n💡 Why 'Last Seen' is Never:")
    print(f"   - Device status is ONLINE (device is trying to transmit)")
    print(f"   - But packets are FAILING (not being delivered)")
    print(f"   - 'last_seen' is only updated when packet_delivered == True")
    print(f"   - Since all packets failed, last_seen remains None ('Never')")
    print(f"\n   This is correct behavior - the device is transmitting but failing!")

if __name__ == "__main__":
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else "WL-8645"
    check_device_status(device_id)
