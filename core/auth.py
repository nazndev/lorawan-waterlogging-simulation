"""
Authentication utilities for password hashing and verification.
Uses bcrypt directly to avoid passlib's initialization issues.
"""
import bcrypt
import logging

logger = logging.getLogger(__name__)

# Use bcrypt directly instead of passlib to avoid initialization issues
# with passlib's internal bug detection that uses long test passwords


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Bcrypt has a 72-byte limit, so we truncate if necessary.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string (bcrypt hash)
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        logger.warning("Password truncated to 72 bytes for bcrypt compatibility")
    
    # Hash using bcrypt directly
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Verify using bcrypt directly
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

