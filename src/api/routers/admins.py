"""
Admin API endpoints for Dating Popcorn Bot
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.exc import IntegrityError
from datetime import timedelta

from ..models import AdminResponse, AdminCreateRequest, AdminLoginRequest, AdminLoginResponse, AdminPasswordUpdateRequest
from ...database.services import AdminService
from ...database.connection import get_session_factory
from ..auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin,
    get_password_hash
)
from ..password_validator import get_password_requirements
from config.settings import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/admins", tags=["admins"])


@router.get("/password-requirements")
async def get_password_requirements_endpoint():
    """
    Get password strength requirements (public endpoint for admin panel)
    """
    return {
        "requirements": get_password_requirements(),
        "rules": [
            "At least 8 characters long",
            "At least one uppercase letter (A-Z)",
            "At least one lowercase letter (a-z)",
            "At least one digit (0-9)",
            "At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)",
            "Not a common or weak password",
            "No repeated characters (e.g., 'aaaaaa')",
            "No sequential characters (e.g., '1234', 'abcd')"
        ]
    }


@router.get("/", response_model=List[AdminResponse])
async def get_admins(current_admin = Depends(get_current_admin)):
    """Get all admins (requires authentication)"""
    try:
        admins = await AdminService.get_all_admins()
        return [
            AdminResponse(
                id=str(admin.id),
                full_name=admin.full_name,
                email=admin.email,
                created_at=admin.created_at
            )
            for admin in admins
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch admins: {str(e)}")


@router.post("/", response_model=AdminResponse)
async def create_admin(admin_data: AdminCreateRequest, current_admin = Depends(get_current_admin)):
    """
    Create a new admin (requires authentication)
    
    Password requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not a common or weak password
    """
    try:
        # Password validation is handled by Pydantic validator in AdminCreateRequest
        # If password is invalid, Pydantic will raise ValidationError before this point
        
        # Check if admin with email already exists
        existing_admin = await AdminService.get_admin_by_email(admin_data.email)
        if existing_admin:
            raise HTTPException(status_code=400, detail="Admin with this email already exists")
        
        admin = await AdminService.create_admin(
            full_name=admin_data.full_name,
            email=admin_data.email,
            password=admin_data.password
        )
        
        return AdminResponse(
            id=str(admin.id),
            full_name=admin.full_name,
            email=admin.email,
            created_at=admin.created_at
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Handle password validation errors from Pydantic
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")


@router.put("/{admin_id}/password")
async def update_admin_password(
    admin_id: str,
    password_data: AdminPasswordUpdateRequest,
    current_admin = Depends(get_current_admin)
):
    """Update an admin's password (requires authentication)"""
    try:
        # Get the admin to update
        admin_to_update = await AdminService.get_admin_by_id(admin_id)
        if not admin_to_update:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        # Update the password (will hash it with bcrypt)
        admin_to_update.set_password(password_data.new_password)
        
        # Save to database
        session_factory = get_session_factory()
        async with session_factory() as session:
            session.add(admin_to_update)
            await session.commit()
            await session.refresh(admin_to_update)
        
        return {"message": "Password updated successfully", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update password: {str(e)}")


@router.put("/by-email/{email}/password")
async def update_admin_password_by_email(
    email: str,
    password_data: AdminPasswordUpdateRequest,
    current_admin = Depends(get_current_admin)
):
    """Update an admin's password by email (requires authentication)"""
    try:
        # Get the admin by email
        admin_to_update = await AdminService.get_admin_by_email(email)
        if not admin_to_update:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        # Update the password (will hash it with bcrypt)
        admin_to_update.set_password(password_data.new_password)
        
        # Save to database
        session_factory = get_session_factory()
        async with session_factory() as session:
            session.add(admin_to_update)
            await session.commit()
            await session.refresh(admin_to_update)
        
        return {"message": "Password updated successfully", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update password: {str(e)}")


@router.delete("/{admin_id}")
async def delete_admin(admin_id: str, current_admin = Depends(get_current_admin)):
    """Delete an admin by ID (requires authentication)"""
    try:
        # Prevent self-deletion
        if str(current_admin.id) == admin_id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        success = await AdminService.delete_admin(admin_id)
        if not success:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        return {"message": "Admin deleted successfully", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete admin: {str(e)}")


@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(login_data: AdminLoginRequest):
    """Login admin with email and password - returns JWT token"""
    try:
        admin = await authenticate_admin(
            email=login_data.email,
            password=login_data.password
        )
        
        if not admin:
            return AdminLoginResponse(
                success=False,
                message="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(admin.id)},
            expires_delta=access_token_expires
        )
        
        return AdminLoginResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            token_type="bearer",
            admin=AdminResponse(
                id=str(admin.id),
                full_name=admin.full_name,
                email=admin.email,
                created_at=admin.created_at
            )
        )
    except ValueError as e:
        # Handle password hash format errors (e.g., old SHA256 hashes)
        error_msg = str(e)
        if "hash format not recognized" in error_msg or "old password format" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        # Re-raise other ValueErrors
        raise HTTPException(status_code=500, detail=f"Login failed: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
