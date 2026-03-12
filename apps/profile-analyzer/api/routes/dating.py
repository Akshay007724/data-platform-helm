from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List, Optional
from services.profile_analyzer import analyze_dating_profile
from models.schemas import ProfileAnalysisResult, DatingPlatform

router = APIRouter(prefix="/api/v1/dating", tags=["Dating Profiles"])


@router.post("/analyze", response_model=ProfileAnalysisResult)
async def analyze_profile(
    platform: DatingPlatform = Form(...),
    notes: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
):
    """
    Analyze a dating profile (Hinge, Bumble, Dil Mil).
    Upload one or more screenshots of the profile.
    """
    if not images:
        raise HTTPException(400, "At least one screenshot is required")
    if len(images) > 10:
        raise HTTPException(400, "Maximum 10 screenshots allowed")

    image_bytes = []
    for img in images:
        content_type = img.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(400, f"File {img.filename} is not an image")
        data = await img.read()
        image_bytes.append(data)

    try:
        result = await analyze_dating_profile(image_bytes, platform.value, notes)
        return result
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")
