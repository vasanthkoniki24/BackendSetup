from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("")
async def list_tenants(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Tenants API is running", "data": []}


@router.post("")
async def create_tenant(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Create tenant endpoint is running"}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Get tenant {tenant_id} endpoint is running"}


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Update tenant {tenant_id} endpoint is running"}


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Delete tenant {tenant_id} endpoint is running"}