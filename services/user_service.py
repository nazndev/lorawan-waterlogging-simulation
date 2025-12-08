"""
User service for authentication and user management.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user import User
from core.auth import hash_password, verify_password
from core.config import APP_CONFIG
import logging

logger = logging.getLogger(__name__)


def create_default_admin(db: Session) -> User:
    """
    Create default admin user if it doesn't exist.
    Called on application startup.
    """
    username = APP_CONFIG["default_admin_username"]
    password = APP_CONFIG["default_admin_password"]
    
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return existing_user
    
    try:
        # Suppress stderr during password hashing to hide bcrypt warnings
        import sys
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            hashed_password = hash_password(password)
        except ValueError as e:
            error_msg = str(e).lower()
            if "72 bytes" in error_msg or "longer than 72" in error_msg:
                # Truncate password and retry (shouldn't happen as hash_password handles this)
                password_bytes = password.encode('utf-8')[:72]
                password = password_bytes.decode('utf-8', errors='ignore')
                hashed_password = hash_password(password)
            else:
                raise
        finally:
            sys.stderr = old_stderr
    except Exception as e:
        # Only log if it's not the 72-byte warning (which is handled internally)
        error_msg = str(e).lower()
        if "72 bytes" not in error_msg and "longer than 72" not in error_msg:
            logger.error(f"Error hashing password: {e}")
            raise
        # If it's the 72-byte error, try one more time with truncation
        password_bytes = password.encode('utf-8')[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
        hashed_password = hash_password(password)
    
    admin_user = User(
        username=username,
        hashed_password=hashed_password,
        is_active=True
    )
    
    try:
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info(f"Default admin user created: {username}")
        return admin_user
    except IntegrityError:
        db.rollback()
        return db.query(User).filter(User.username == username).first()
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
        # Return existing user if creation failed
        return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> User:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username
        password: Plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def get_user_by_username(db: Session, username: str) -> User:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()

