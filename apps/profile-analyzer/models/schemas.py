from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class DatingPlatform(str, Enum):
    HINGE = "hinge"
    BUMBLE = "bumble"
    DIL_MIL = "dil_mil"


class AnalysisScore(BaseModel):
    category: str
    score: float  # 0-10
    feedback: str


class ProfileAnalysisResult(BaseModel):
    platform: str
    overall_score: float
    scores: List[AnalysisScore]
    strengths: List[str]
    improvements: List[str]
    action_items: List[str]
    full_analysis: str


class LinkedInJobData(BaseModel):
    title: str
    company: str
    location: str
    description: str
    requirements: List[str]
    url: str
    easy_apply: bool = False


class LinkedInProfileResult(BaseModel):
    name: str
    headline: str
    overall_score: float
    scores: List[AnalysisScore]
    strengths: List[str]
    improvements: List[str]
    action_items: List[str] = []
    keyword_suggestions: List[str]
    full_analysis: str


class ResumeOptimizeResult(BaseModel):
    job_title: str
    company: str
    match_score: float
    key_changes: List[str]
    keywords_added: List[str]
    download_filename: str


class ApplicantInfo(BaseModel):
    name: str
    email: str
    phone: str
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    years_experience: Optional[int] = None
    cover_letter_note: Optional[str] = None


class AutoApplyResult(BaseModel):
    job_title: str
    company: str
    job_url: str
    status: str  # "applied", "manual_required", "easy_apply_unavailable", "error"
    message: str
    applied_at: Optional[str] = None
