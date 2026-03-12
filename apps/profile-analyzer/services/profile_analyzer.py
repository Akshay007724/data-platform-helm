import base64
import json
import re
from typing import Optional
from models.schemas import ProfileAnalysisResult, AnalysisScore, LinkedInProfileResult
from services.llm_client import get_client, VISION_MODEL, TEXT_MODEL

PLATFORM_PROMPTS = {
    "hinge": """You are an expert dating coach specializing in Hinge profiles. Analyze the profile screenshots and give brutally honest, actionable feedback.

Evaluate these categories (score each 0-10):
1. **Photos**: variety, quality, lifestyle portrayal, how attractive/approachable they make you look, backgrounds, expressions
2. **Prompts & Answers**: creativity, conversational hooks, humor, authenticity, uniqueness vs generic answers
3. **Overall Vibe**: first impression, personality coming through, desirability
4. **Profile Completeness**: are all prompts used well, any wasted opportunities

Respond in this exact JSON format:
{
  "scores": [
    {"category": "Photos", "score": X.X, "feedback": "specific feedback"},
    {"category": "Prompts & Answers", "score": X.X, "feedback": "specific feedback"},
    {"category": "Overall Vibe", "score": X.X, "feedback": "specific feedback"},
    {"category": "Profile Completeness", "score": X.X, "feedback": "specific feedback"}
  ],
  "overall_score": X.X,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "action_items": ["action 1", "action 2", "action 3", "action 4", "action 5"],
  "full_analysis": "comprehensive 2-3 paragraph analysis"
}""",

    "bumble": """You are an expert dating coach specializing in Bumble profiles. Analyze the profile screenshots and provide detailed, actionable feedback.

Bumble context: Women message first, so male profiles need to be highly attractive and intriguing. For women, the profile needs to prompt easy conversation starters.

Evaluate these categories (score each 0-10):
1. **Photos**: main photo impact, variety (lifestyle/social/solo), quality and lighting
2. **Bio**: authenticity, humor, conversation starter potential, length appropriateness
3. **Interests/Badges**: relevance, conversation potential
4. **Opening Move Readiness**: how easy does this profile make it for someone to message

Respond in this exact JSON format:
{
  "scores": [
    {"category": "Photos", "score": X.X, "feedback": "specific feedback"},
    {"category": "Bio", "score": X.X, "feedback": "specific feedback"},
    {"category": "Interests & Badges", "score": X.X, "feedback": "specific feedback"},
    {"category": "Conversation Starter Potential", "score": X.X, "feedback": "specific feedback"}
  ],
  "overall_score": X.X,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "action_items": ["action 1", "action 2", "action 3", "action 4", "action 5"],
  "full_analysis": "comprehensive 2-3 paragraph analysis"
}""",

    "dil_mil": """You are an expert dating coach specializing in Dil Mil, the South Asian dating app. Analyze the profile screenshots with cultural awareness and dating expertise.

Dil Mil context: Platform for South Asian singles and their admirers. Cultural background, family values, and heritage often matter. Balance modern dating appeal with cultural authenticity.

Evaluate these categories (score each 0-10):
1. **Photos**: quality, variety, cultural representation, professional-personal balance
2. **Bio/About**: personality, values communication, cultural pride vs stereotyping, uniqueness
3. **Cultural & Lifestyle Signals**: how well the profile conveys lifestyle, values, ambitions
4. **Compatibility Signals**: does the profile attract the right matches for serious relationships

Respond in this exact JSON format:
{
  "scores": [
    {"category": "Photos", "score": X.X, "feedback": "specific feedback"},
    {"category": "Bio & About", "score": X.X, "feedback": "specific feedback"},
    {"category": "Cultural & Lifestyle Signals", "score": X.X, "feedback": "specific feedback"},
    {"category": "Compatibility Signals", "score": X.X, "feedback": "specific feedback"}
  ],
  "overall_score": X.X,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "action_items": ["action 1", "action 2", "action 3", "action 4", "action 5"],
  "full_analysis": "comprehensive 2-3 paragraph analysis"
}""",

    "linkedin": """You are an executive LinkedIn coach and personal branding expert. Analyze this LinkedIn profile and provide comprehensive professional feedback.

Evaluate these categories (score each 0-10):
1. **Profile Photo**: professionalism, approachability, quality
2. **Headline**: clarity, keyword richness, differentiation, value proposition
3. **About Section**: narrative quality, value proposition, call to action, storytelling
4. **Experience Descriptions**: achievement-focus, impact quantification, STAR format
5. **Skills & Endorsements**: relevance, coverage, strategic positioning
6. **Overall Completeness**: profile strength indicator

Respond in this exact JSON format:
{
  "scores": [
    {"category": "Profile Photo", "score": X.X, "feedback": "specific feedback"},
    {"category": "Headline", "score": X.X, "feedback": "specific feedback"},
    {"category": "About Section", "score": X.X, "feedback": "specific feedback"},
    {"category": "Experience Descriptions", "score": X.X, "feedback": "specific feedback"},
    {"category": "Skills & Endorsements", "score": X.X, "feedback": "specific feedback"},
    {"category": "Overall Completeness", "score": X.X, "feedback": "specific feedback"}
  ],
  "overall_score": X.X,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "action_items": ["action 1", "action 2", "action 3", "action 4", "action 5"],
  "keyword_suggestions": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "full_analysis": "comprehensive 2-3 paragraph professional analysis"
}"""
}


async def analyze_dating_profile(
    images: list[bytes],
    platform: str,
    notes: Optional[str] = None
) -> ProfileAnalysisResult:
    """Analyze dating profile screenshots using GLM-4V vision."""

    content = []

    # GLM-4V uses OpenAI-compatible image_url format (data URIs for base64)
    for img_bytes in images:
        b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    prompt = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS["hinge"])
    if notes:
        prompt += f"\n\nAdditional context from user: {notes}"

    content.append({"type": "text", "text": prompt})

    response = get_client().chat.completions.create(
        model=VISION_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    text = response.choices[0].message.content

    # Parse JSON from response
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        raise ValueError("Could not parse analysis response")

    data = json.loads(json_match.group())

    return ProfileAnalysisResult(
        platform=platform,
        overall_score=data["overall_score"],
        scores=[AnalysisScore(**s) for s in data["scores"]],
        strengths=data["strengths"],
        improvements=data["improvements"],
        action_items=data["action_items"],
        full_analysis=data["full_analysis"]
    )


async def analyze_linkedin_profile_text(profile_text: str) -> LinkedInProfileResult:
    """Analyze LinkedIn profile from extracted text using GLM-4."""

    prompt = PLATFORM_PROMPTS["linkedin"]

    response = get_client().chat.completions.create(
        model=TEXT_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"Here is the LinkedIn profile data:\n\n{profile_text}\n\n{prompt}"
        }]
    )

    text = response.choices[0].message.content

    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        raise ValueError("Could not parse analysis response")

    data = json.loads(json_match.group())

    return LinkedInProfileResult(
        name=data.get("name", "Unknown"),
        headline=data.get("headline", ""),
        overall_score=data["overall_score"],
        scores=[AnalysisScore(**s) for s in data["scores"]],
        strengths=data["strengths"],
        improvements=data["improvements"],
        action_items=data.get("action_items", []),
        keyword_suggestions=data.get("keyword_suggestions", []),
        full_analysis=data["full_analysis"]
    )
