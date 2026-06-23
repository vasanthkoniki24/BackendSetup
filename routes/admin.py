from fastapi import APIRouter, Depends
from core.dependencies import get_current_admin
from models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_admin)):
    return {"success": True, "message": "Admin dashboard API is running"}


@router.get("/stats")
async def admin_stats(current_user: User = Depends(get_current_admin)):
    return {"success": True, "message": "Admin stats API is running", "data": {}}


@router.get("/logs")
async def admin_logs(current_user: User = Depends(get_current_admin)):
    return {"success": True, "message": "Admin logs API is running", "data": []}