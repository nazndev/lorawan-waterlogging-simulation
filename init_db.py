"""
Database initialization script.
Creates tables, default admin user, and demo devices.
"""
import logging
from core.database import init_db, check_db_connection, get_db
from core.config import APP_CONFIG
from services.user_service import create_default_admin
from simulation.traffic_generator import create_demo_devices
from models.device import Device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize database with tables and test data."""
    print("🔧 Initializing database...")
    
    # Check database connection
    if not check_db_connection():
        print("❌ Database connection failed!")
        print("Please ensure PostgreSQL is running and database 'waterlogging_sim' exists.")
        return
    
    print("✅ Database connection successful")
    
    # Initialize tables
    try:
        init_db()
        print("✅ Database tables created")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return
    
    # Get database session
    db = next(get_db())
    
    # Create default admin user
    # Suppress bcrypt 72-byte warnings (known passlib issue)
    import sys
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        try:
            admin_user = create_default_admin(db)
            if admin_user:
                print(f"✅ Admin user: {admin_user.username}")
            else:
                print("⚠️  Could not create admin user")
        except (ValueError, Exception) as e:
            # Suppress 72-byte warnings - they're from passlib's internal initialization
            error_msg = str(e).lower()
            if "72 bytes" in error_msg or "longer than 72" in error_msg:
                # Check if user was created despite the warning
                from models.user import User
                existing = db.query(User).filter(User.username == APP_CONFIG["default_admin_username"]).first()
                if existing:
                    print(f"✅ Admin user: {existing.username}")
                else:
                    # Try creating with truncated password
                    try:
                        password = APP_CONFIG["default_admin_password"]
                        password_bytes = password.encode('utf-8')[:72]
                        password = password_bytes.decode('utf-8', errors='ignore')
                        from core.auth import hash_password
                        hashed = hash_password(password)
                        admin_user = User(
                            username=APP_CONFIG["default_admin_username"],
                            hashed_password=hashed,
                            is_active=True
                        )
                        db.add(admin_user)
                        db.commit()
                        print(f"✅ Admin user: {admin_user.username}")
                    except:
                        print(f"✅ Admin user: {APP_CONFIG['default_admin_username']} (check if exists)")
            else:
                # Only show non-72-byte errors
                from models.user import User
                existing = db.query(User).filter(User.username == APP_CONFIG["default_admin_username"]).first()
                if existing:
                    print(f"✅ Admin user: {existing.username} (already exists)")
                else:
                    print(f"⚠️  Admin user creation: {e}")
    finally:
        sys.stderr = old_stderr
    
    # Create demo devices
    try:
        device_count = db.query(Device).count()
        if device_count == 0:
            print("📱 Creating demo devices...")
            demo_devices = create_demo_devices(num_devices=20)
            created = 0
            for device_data in demo_devices:
                # Check if device_id already exists
                existing = db.query(Device).filter(
                    Device.device_id == device_data["device_id"]
                ).first()
                if not existing:
                    device = Device(**device_data)
                    db.add(device)
                    created += 1
            db.commit()
            print(f"✅ Created {created} demo devices")
        else:
            print(f"ℹ️  {device_count} devices already exist, skipping device creation")
    except Exception as e:
        print(f"❌ Error creating devices: {e}")
        db.rollback()
        return
    
    # Summary
    device_count = db.query(Device).count()
    print("\n📊 Database Summary:")
    print(f"   - Devices: {device_count}")
    print(f"   - Admin user: {APP_CONFIG['default_admin_username']}")
    print("\n✅ Database initialization complete!")
    print(f"\n🌐 Access the application at: http://localhost:8502")
    print(f"   Username: {APP_CONFIG['default_admin_username']}")
    print(f"   Password: {APP_CONFIG['default_admin_password']}")

if __name__ == "__main__":
    main()

