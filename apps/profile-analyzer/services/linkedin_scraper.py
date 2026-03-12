import json
import re
from typing import Optional
from playwright.async_api import async_playwright, Page
from models.schemas import LinkedInJobData, AutoApplyResult, ApplicantInfo
from services.llm_client import get_client, TEXT_MODEL


def _get_cookies(li_at: str) -> list:
    """Build LinkedIn cookie list from li_at value."""
    return [
        {
            "name": "li_at",
            "value": li_at,
            "domain": ".linkedin.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
        }
    ]


async def _create_context(playwright, li_at: Optional[str] = None, headless: bool = True):
    """Create a Playwright browser context with anti-detection measures."""
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ]
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )

    # Anti-detection
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        window.chrome = { runtime: {} };
    """)

    if li_at:
        await context.add_cookies(_get_cookies(li_at))

    return browser, context


async def scrape_job(url: str, li_at: Optional[str] = None) -> LinkedInJobData:
    """Scrape a LinkedIn job posting."""
    async with async_playwright() as p:
        browser, context = await _create_context(p, li_at)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Try to expand "Show more" for job description
            try:
                show_more = page.locator("button[aria-label*='more']").first
                await show_more.click(timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # Extract job data
            title = await page.locator(
                "h1.job-details-jobs-unified-top-card__job-title, h1.t-24"
            ).first.inner_text(timeout=5000)

            company = ""
            try:
                company = await page.locator(
                    ".job-details-jobs-unified-top-card__company-name a, .topcard__org-name-link"
                ).first.inner_text(timeout=3000)
            except Exception:
                pass

            location = ""
            try:
                location = await page.locator(
                    ".job-details-jobs-unified-top-card__bullet, .topcard__flavor--bullet"
                ).first.inner_text(timeout=3000)
            except Exception:
                pass

            # Get full description
            description = ""
            try:
                desc_el = page.locator(
                    ".jobs-description-content__text, .description__text"
                ).first
                description = await desc_el.inner_text(timeout=5000)
            except Exception:
                pass

            # Check for Easy Apply
            easy_apply = False
            try:
                apply_btn = page.locator(
                    "button.jobs-apply-button, button[aria-label*='Easy Apply']"
                ).first
                btn_text = await apply_btn.inner_text(timeout=3000)
                easy_apply = "easy apply" in btn_text.lower()
            except Exception:
                pass

            # Extract requirements using Claude
            requirements = await _extract_requirements(description)

            return LinkedInJobData(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                description=description,
                requirements=requirements,
                url=url,
                easy_apply=easy_apply,
            )
        finally:
            await browser.close()


async def _extract_requirements(description: str) -> list[str]:
    """Use Claude to extract key requirements from job description."""
    if not description:
        return []

    response = get_client().chat.completions.create(
        model=TEXT_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Extract the top 10 most important requirements from this job description as a JSON array of strings.
Focus on: required skills, years of experience, education, tools/technologies, and key responsibilities.

Job description:
{description[:3000]}

Return ONLY a JSON array like: ["requirement 1", "requirement 2", ...]"""
        }]
    )

    text = response.choices[0].message.content
    match = re.search(r'\[.*?\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


async def scrape_linkedin_profile(url: str, li_at: str) -> dict:
    """Scrape a LinkedIn profile page."""
    async with async_playwright() as p:
        browser, context = await _create_context(p, li_at)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            profile_data = {}

            # Name
            try:
                profile_data["name"] = await page.locator(
                    "h1.text-heading-xlarge, h1.pv-text-details__left-panel h1"
                ).first.inner_text(timeout=5000)
            except Exception:
                profile_data["name"] = "Unknown"

            # Headline
            try:
                profile_data["headline"] = await page.locator(
                    ".text-body-medium.break-words"
                ).first.inner_text(timeout=3000)
            except Exception:
                profile_data["headline"] = ""

            # About
            try:
                # Try to expand about section
                about_more = page.locator(
                    "#about ~ div button, .pv-about__see-more"
                ).first
                await about_more.click(timeout=2000)
                await page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                profile_data["about"] = await page.locator(
                    "#about ~ .display-flex .visually-hidden, "
                    ".pv-about-section .pv-about__summary-text"
                ).first.inner_text(timeout=3000)
            except Exception:
                profile_data["about"] = ""

            # Experience
            experience_items = []
            try:
                exp_section = page.locator(
                    "#experience ~ .pvs-list li.artdeco-list__item"
                )
                count = await exp_section.count()
                for i in range(min(count, 5)):
                    try:
                        item_text = await exp_section.nth(i).inner_text(timeout=2000)
                        experience_items.append(item_text.strip())
                    except Exception:
                        pass
            except Exception:
                pass
            profile_data["experience"] = experience_items

            # Skills
            skills = []
            try:
                skill_items = page.locator(
                    "#skills ~ .pvs-list li .visually-hidden"
                )
                count = await skill_items.count()
                for i in range(min(count, 10)):
                    try:
                        skill = await skill_items.nth(i).inner_text(timeout=1000)
                        skills.append(skill.strip())
                    except Exception:
                        pass
            except Exception:
                pass
            profile_data["skills"] = skills

            # Format for analysis
            profile_text = f"""
Name: {profile_data.get('name', 'Unknown')}
Headline: {profile_data.get('headline', '')}

About:
{profile_data.get('about', 'Not provided')}

Experience:
{chr(10).join(profile_data.get('experience', [])) or 'Not scraped'}

Skills:
{', '.join(profile_data.get('skills', [])) or 'Not scraped'}
"""
            profile_data["raw_text"] = profile_text
            return profile_data

        finally:
            await browser.close()


async def easy_apply_job(
    job_url: str,
    resume_path: str,
    applicant: ApplicantInfo,
    li_at: str,
    headless: bool = True,
) -> AutoApplyResult:
    """
    Auto-apply to a LinkedIn job using Easy Apply.
    Handles multi-step application forms.
    """
    from datetime import datetime

    async with async_playwright() as p:
        browser, context = await _create_context(p, li_at, headless=headless)
        page = await context.new_page()

        try:
            await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Get job title and company for result
            job_title = "Unknown Position"
            company = "Unknown Company"
            try:
                job_title = await page.locator("h1").first.inner_text(timeout=5000)
                company = await page.locator(
                    ".job-details-jobs-unified-top-card__company-name a"
                ).first.inner_text(timeout=3000)
            except Exception:
                pass

            # Find and click Easy Apply button
            easy_apply_btn = None
            try:
                for selector in [
                    "button.jobs-apply-button[aria-label*='Easy Apply']",
                    "button[aria-label*='Easy Apply']",
                    ".jobs-apply-button",
                ]:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        btn_text = await btn.inner_text(timeout=1000)
                        if "easy apply" in btn_text.lower():
                            easy_apply_btn = btn
                            break
            except Exception:
                pass

            if not easy_apply_btn:
                return AutoApplyResult(
                    job_title=job_title.strip(),
                    company=company.strip(),
                    job_url=job_url,
                    status="easy_apply_unavailable",
                    message=(
                        "This job does not have Easy Apply. "
                        "Please apply manually via the company website."
                    ),
                )

            await easy_apply_btn.click()
            await page.wait_for_timeout(2000)

            # Handle the application modal/form
            max_steps = 10
            step = 0
            submitted = False

            while step < max_steps:
                step += 1
                await page.wait_for_timeout(1500)

                # Check if application is complete
                for success_text in [
                    "Application submitted",
                    "application was sent",
                    "You applied",
                ]:
                    try:
                        if await page.locator(f"text={success_text}").is_visible(timeout=1000):
                            submitted = True
                            break
                    except Exception:
                        pass

                if submitted:
                    break

                # Handle resume upload step
                resume_upload = page.locator("input[type='file']").first
                try:
                    if await resume_upload.is_visible(timeout=1000):
                        await resume_upload.set_input_files(resume_path)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

                # Fill contact info fields
                await _fill_contact_fields(page, applicant)

                # Handle radio buttons / dropdowns for experience
                await _handle_experience_fields(page, applicant)

                # Handle text questions with Claude
                await _answer_text_questions(page, job_title, applicant)

                # Click Next or Review or Submit
                advanced = False
                for btn_label in [
                    "Submit application",
                    "Review your application",
                    "Next",
                    "Continue to next step",
                    "Review",
                ]:
                    try:
                        btn = page.locator(
                            f"button[aria-label='{btn_label}'], "
                            f"button:has-text('{btn_label}')"
                        ).first
                        if (
                            await btn.is_visible(timeout=1000)
                            and await btn.is_enabled(timeout=1000)
                        ):
                            await btn.click()
                            await page.wait_for_timeout(1500)
                            advanced = True

                            if "submit" in btn_label.lower():
                                submitted = True
                            break
                    except Exception:
                        pass

                if submitted:
                    break

                if not advanced:
                    # Try a generic next button
                    try:
                        btns = page.locator("button[type='button']")
                        count = await btns.count()
                        for i in range(count):
                            btn = btns.nth(i)
                            text = await btn.inner_text(timeout=500)
                            if any(
                                w in text.lower()
                                for w in ["next", "continue", "submit", "review"]
                            ):
                                await btn.click()
                                advanced = True
                                break
                    except Exception:
                        pass

                if not advanced:
                    break

            if submitted:
                return AutoApplyResult(
                    job_title=job_title.strip(),
                    company=company.strip(),
                    job_url=job_url,
                    status="applied",
                    message=f"Successfully applied to {job_title} at {company}.",
                    applied_at=datetime.now().isoformat(),
                )
            else:
                return AutoApplyResult(
                    job_title=job_title.strip(),
                    company=company.strip(),
                    job_url=job_url,
                    status="manual_required",
                    message=(
                        "Could not complete the application automatically. "
                        "Some steps may require manual input. Please complete the application manually."
                    ),
                )

        except Exception as e:
            return AutoApplyResult(
                job_title="Unknown",
                company="Unknown",
                job_url=job_url,
                status="error",
                message=f"Error during application: {str(e)}",
            )
        finally:
            await browser.close()


async def _fill_contact_fields(page: Page, applicant: ApplicantInfo):
    """Fill standard contact information fields."""
    field_map = {
        "email": applicant.email,
        "phone": applicant.phone,
        "name": applicant.name,
        "first": applicant.name.split()[0] if applicant.name else "",
        "last": (
            applicant.name.split()[-1]
            if applicant.name and len(applicant.name.split()) > 1
            else ""
        ),
        "city": applicant.location or "",
        "location": applicant.location or "",
    }

    for key, value in field_map.items():
        if not value:
            continue
        for selector in [
            f"input[name*='{key}' i]",
            f"input[id*='{key}' i]",
            f"input[placeholder*='{key}' i]",
        ]:
            try:
                fields = page.locator(selector)
                count = await fields.count()
                for i in range(count):
                    field = fields.nth(i)
                    if await field.is_visible(timeout=500):
                        current = await field.input_value()
                        if not current:
                            await field.fill(value)
            except Exception:
                pass


async def _handle_experience_fields(page: Page, applicant: ApplicantInfo):
    """Handle years of experience dropdowns and radio buttons."""
    if not applicant.years_experience:
        return

    years = applicant.years_experience

    # Handle dropdowns that ask for years of experience
    try:
        selects = page.locator("select")
        count = await selects.count()
        for i in range(count):
            sel = selects.nth(i)
            if await sel.is_visible(timeout=500):
                try:
                    label = await page.locator("label[for]").nth(i).inner_text(timeout=500)
                    if "year" in label.lower() or "experience" in label.lower():
                        options = await sel.locator("option").all_inner_texts()
                        for opt in options:
                            try:
                                m = re.search(r'\d+', opt)
                                low = int(m.group()) if m else -1
                                if low <= years:
                                    await sel.select_option(label=opt)
                                    break
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass


async def _answer_text_questions(page: Page, job_title: str, applicant: ApplicantInfo):
    """Use Claude to answer open-ended application questions."""
    try:
        textareas = page.locator("textarea")
        count = await textareas.count()

        for i in range(count):
            ta = textareas.nth(i)
            if not await ta.is_visible(timeout=500):
                continue

            current = await ta.input_value()
            if current:
                continue  # Already filled

            # Find the associated question label
            question_text = ""
            try:
                parent = ta.locator("xpath=ancestor::div[@class][1]")
                question_text = await parent.locator(
                    "label, p, span.t-14"
                ).first.inner_text(timeout=1000)
            except Exception:
                continue

            if not question_text:
                continue

            # Use local text model to answer application questions
            response = get_client().chat.completions.create(
                model=TEXT_MODEL,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": f"""Answer this job application question concisely and professionally (2-3 sentences max).

Question: {question_text}
Applying for: {job_title}
Applicant name: {applicant.name}
Years of experience: {applicant.years_experience or 'Not specified'}

Write a genuine, confident answer in first person."""
                }]
            )

            answer = response.choices[0].message.content
            await ta.fill(answer.strip())
    except Exception:
        pass
