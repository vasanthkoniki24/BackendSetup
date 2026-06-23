from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/ai/document", tags=["AI Document"])


@router.post("/analyze")
async def analyze_document(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Document analyze endpoint is running"}


@router.post("/summarize")
async def summarize_document(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Document summarize endpoint is running"}


@router.post("/extract")
async def extract_data(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Document extract endpoint is running"}


@router.get("/history")
async def document_history(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Document history endpoint is running", "data": []}