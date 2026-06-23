from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/ai/resume", tags=["AI Resume"])


@router.post("/analyze")
async def analyze_resume(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Resume analyze endpoint is running"}


@router.post("/score")
async def score_resume(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Resume score endpoint is running"}


@router.post("/interview-questions")
async def generate_interview_questions(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Resume interview questions endpoint is running"}


@router.get("/history")
async def resume_history(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "AI Resume history endpoint is running", "data": []}