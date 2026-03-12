from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import os
import tempfile
import uuid
from services.resume_optimizer import parse_resume, optimize_resume
from services.linkedin_scraper import scrape_job, easy_apply_job
from models.schemas import ResumeOptimizeResult, AutoApplyResult, ApplicantInfo

router = APIRouter(prefix="/api/v1/resume", tags=["Resume"])

# Store optimized resumes temporarily (keyed by download_id)
_resume_store: dict[str, bytes] = {}


@router.post("/optimize")
async def optimize_resume_endpoint(
    job_url: str = Form(...),
    resume: UploadFile = File(...),
    li_at_cookie: Optional[str] = Form(None),
):
    """
    Optimize a resume for a specific LinkedIn job.
    Returns metadata and a download token for the optimized DOCX.
    """
    allowed_extensions = (".pdf", ".docx", ".doc")
    filename = resume.filename or "resume.pdf"
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(400, "Please upload a PDF or DOCX resume")

    resume_bytes = await resume.read()

    # Scrape job
    li_at = li_at_cookie or os.getenv("LINKEDIN_LI_AT_COOKIE")
    try:
        job_data = await scrape_job(job_url, li_at)
    except Exception as e:
        raise HTTPException(500, f"Could not fetch job posting: {str(e)}")

    # Parse resume
    try:
        resume_text = parse_resume(resume_bytes, filename)
    except Exception as e:
        raise HTTPException(400, f"Could not parse resume: {str(e)}")

    # Optimize
    try:
        docx_bytes, metadata = await optimize_resume(resume_text, job_data.__dict__)
    except Exception as e:
        raise HTTPException(500, f"Optimization failed: {str(e)}")

    # Store for download
    download_id = str(uuid.uuid4())
    _resume_store[download_id] = docx_bytes

    safe_company = "".join(
        c for c in job_data.company if c.isalnum() or c == "_"
    )[:20]
    download_filename = f"resume_{safe_company}_optimized.docx"

    return {
        "job_title": metadata["job_title"],
        "company": metadata["company"],
        "match_score": metadata["match_score"],
        "key_changes": metadata["key_changes"],
        "keywords_added": metadata["keywords_added"],
        "download_id": download_id,
        "download_filename": download_filename,
    }


@router.get("/download/{download_id}")
async def download_resume(
    download_id: str,
    filename: str = "resume_optimized.docx",
):
    """Download an optimized resume by its download ID."""
    if download_id not in _resume_store:
        raise HTTPException(404, "Resume not found. It may have expired.")

    docx_bytes = _resume_store[download_id]

    # Write to temp file for response
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.write(docx_bytes)
    tmp.close()

    return FileResponse(
        tmp.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename=filename,
    )


@router.post("/apply", response_model=AutoApplyResult)
async def auto_apply_job(
    job_url: str = Form(...),
    resume: UploadFile = File(...),
    applicant_name: str = Form(...),
    applicant_email: str = Form(...),
    applicant_phone: str = Form(...),
    applicant_location: Optional[str] = Form(None),
    applicant_linkedin_url: Optional[str] = Form(None),
    years_experience: Optional[int] = Form(None),
    li_at_cookie: str = Form(...),
    optimize_first: bool = Form(True),
):
    """
    Auto-apply to a LinkedIn job using Easy Apply.
    Optionally optimizes the resume before applying.
    """
    resume_bytes = await resume.read()
    filename = resume.filename or "resume.pdf"

    # Scrape job
    try:
        job_data = await scrape_job(job_url, li_at_cookie)
    except Exception as e:
        raise HTTPException(500, f"Could not fetch job posting: {str(e)}")

    if not job_data.easy_apply:
        return AutoApplyResult(
            job_title=job_data.title,
            company=job_data.company,
            job_url=job_url,
            status="easy_apply_unavailable",
            message=(
                "This job requires applying on the company's website. "
                "Please apply manually."
            ),
        )

    applicant = ApplicantInfo(
        name=applicant_name,
        email=applicant_email,
        phone=applicant_phone,
        location=applicant_location,
        linkedin_url=applicant_linkedin_url,
        years_experience=years_experience,
    )

    resume_path = None
    try:
        if optimize_first:
            resume_text = parse_resume(resume_bytes, filename)
            docx_bytes, _ = await optimize_resume(resume_text, job_data.__dict__)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
            tmp.write(docx_bytes)
            tmp.close()
            resume_path = tmp.name
        else:
            ext = ".pdf" if filename.lower().endswith(".pdf") else ".docx"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(resume_bytes)
            tmp.close()
            resume_path = tmp.name

        result = await easy_apply_job(
            job_url, resume_path, applicant, li_at_cookie
        )
        return result
    finally:
        if resume_path and os.path.exists(resume_path):
            os.unlink(resume_path)
