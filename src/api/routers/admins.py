"""
Admin API endpoints for Dating Popcorn Bot
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.exc import IntegrityError

from ..models import AdminResponse, AdminCreateRequest, AdminLoginRequest, AdminLoginResponse
from ...database.services import AdminService

router = APIRouter(prefix="/admins", tags=["admins"])


@router.get("/", response_model=List[AdminResponse])
async def get_admins():
    """Get all admins"""
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
async def create_admin(admin_data: AdminCreateRequest):
    """Create a new admin"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")


@router.delete("/{admin_id}")
async def delete_admin(admin_id: str):
    """Delete an admin by ID"""
    try:
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
    """Login admin with email and password"""
    try:
        admin = await AdminService.authenticate_admin(
            email=login_data.email,
            password=login_data.password
        )
        
        if not admin:
            return AdminLoginResponse(
                success=False,
                message="Invalid email or password"
            )
        
        return AdminLoginResponse(
            success=True,
            message="Login successful",
            admin=AdminResponse(
                id=str(admin.id),
                full_name=admin.full_name,
                email=admin.email,
                created_at=admin.created_at
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
