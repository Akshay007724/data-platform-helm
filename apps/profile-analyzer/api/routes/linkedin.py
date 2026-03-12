from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.linkedin_scraper import scrape_job, scrape_linkedin_profile
from services.profile_analyzer import analyze_linkedin_profile_text
from models.schemas import LinkedInJobData, LinkedInProfileResult
import os

router = APIRouter(prefix="/api/v1/linkedin", tags=["LinkedIn"])


class ProfileAnalyzeRequest(BaseModel):
    profile_url: str
    li_at_cookie: Optional[str] = None


class JobScrapeRequest(BaseModel):
    job_url: str
    li_at_cookie: Optional[str] = None


@router.post("/analyze-profile", response_model=LinkedInProfileResult)
async def analyze_linkedin_profile(req: ProfileAnalyzeRequest):
    """
    Scrape and analyze a LinkedIn profile.
    Provide li_at_cookie for private profiles (export from browser).
    """
    li_at = req.li_at_cookie or os.getenv("LINKEDIN_LI_AT_COOKIE")

    if not li_at:
        raise HTTPException(
            400,
            "LinkedIn li_at cookie is required. Add it in Settings."
        )

    try:
        profile_data = await scrape_linkedin_profile(req.profile_url, li_at)
        result = await analyze_linkedin_profile_text(profile_data["raw_text"])
        # Override name/headline from scraped data
        result.name = profile_data.get("name", result.name)
        result.headline = profile_data.get("headline", result.headline)
        return result
    except Exception as e:
        raise HTTPException(500, f"Profile analysis failed: {str(e)}")


@router.post("/scrape-job", response_model=LinkedInJobData)
async def scrape_job_posting(req: JobScrapeRequest):
    """Scrape a LinkedIn job posting to get title, company, requirements, and description."""
    li_at = req.li_at_cookie or os.getenv("LINKEDIN_LI_AT_COOKIE")

    try:
        job_data = await scrape_job(req.job_url, li_at)
        return job_data
    except Exception as e:
        raise HTTPException(500, f"Job scraping failed: {str(e)}")
