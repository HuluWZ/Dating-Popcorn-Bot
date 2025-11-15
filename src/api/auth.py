"""
Authentication utilities for Dating Popcorn Bot API
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from config.settings import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.database.services import AdminService

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admins/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Returns True if password matches, False otherwise.
    Raises ValueError if the hash format is not recognized (e.g., old SHA256 hashes).
    """
    try:
        # Bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
        
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        # Handle unrecognized hash formats (e.g., old SHA256 hashes)
        error_msg = str(e).lower()
        if "hash could not be identified" in error_msg or "unrecognized hash" in error_msg:
            raise ValueError(
                "Password hash format not recognized. This account may have an old password format. "
                "Please contact an administrator to reset your password."
            ) from e
        # Handle bcrypt password length errors
        if "password cannot be longer than 72 bytes" in error_msg:
            raise ValueError(
                "Password is too long. Maximum length is 72 bytes. Please use a shorter password."
            ) from e
        # Re-raise other errors
        raise


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Note: Bcrypt has a 72-byte limit. Passwords longer than 72 bytes will be truncated.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """
    Dependency to get the current authenticated admin from JWT token
    
    Raises HTTPException if token is invalid or admin not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        admin_id: str = payload.get("sub")
        if admin_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get admin from database
    admin = await AdminService.get_admin_by_id(admin_id)
    if admin is None:
        raise credentials_exception
    
    return admin


async def authenticate_admin(email: str, password: str):
    """
    Authenticate an admin with email and password
    
    Returns admin if credentials are valid, None otherwise.
    Raises ValueError if password hash format is not recognized (e.g., old SHA256 hashes).
    
    Note: Uses the admin model's check_password method which uses bcrypt for secure password hashing.
    """
    admin = await AdminService.get_admin_by_email(email)
    if not admin:
        return None
    
    # Check password using the admin's check_password method
    # The admin model uses bcrypt for secure password hashing
    try:
        if admin.check_password(password):
            return admin
    except ValueError as e:
        # Re-raise ValueError from verify_password (hash format issues)
        raise
    
    return None

