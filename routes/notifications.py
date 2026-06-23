from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Notifications API is running", "data": []}


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Notification {notification_id} marked as read"}


@router.post("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Notification {notification_id} deleted"}