from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("")
async def list_subscriptions(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Subscriptions API is running", "data": []}


@router.post("")
async def create_subscription(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Create subscription endpoint is running"}


@router.get("/{subscription_id}")
async def get_subscription(subscription_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Get subscription {subscription_id} endpoint is running"}


@router.patch("/{subscription_id}")
async def update_subscription(subscription_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Update subscription {subscription_id} endpoint is running"}


@router.delete("/{subscription_id}")
async def cancel_subscription(subscription_id: int, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": f"Cancel subscription {subscription_id} endpoint is running"}