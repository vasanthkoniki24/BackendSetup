from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/ai/chatbot", tags=["AI Chatbot"])


@router.post("/chat")
async def chat(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Chatbot chat endpoint is running"}


@router.get("/history")
async def chat_history(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Chatbot history endpoint is running", "data": []}


@router.delete("/history")
async def clear_history(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Chatbot history cleared"}