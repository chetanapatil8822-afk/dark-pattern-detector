
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import time

from backend.utils.db import get_db
from backend.services.scraper import scrape_website, extract_domain
from backend.services.ai_analyzer import (
    analyze_with_gemini,
    analyze_text_content,
    calculate_credibility_score,
    get_severity_label
)
from backend.services.demo_results import DEMO_MODE, DEMO_RESULTS
from backend.models.models import AnalysisResult, DetectedPattern

router = APIRouter()


class URLAnalysisRequest(BaseModel):
    url: str
    include_screenshot: bool = False


class TextAnalysisRequest(BaseModel):
    content: str
    url: Optional[str] = "manual-input"
    description: Optional[str] = ""


def save_analysis(db, url, domain, ai_result, patterns, duration):
    """Helper to save analysis and patterns to DB"""
    credibility_score = ai_result.get(
    "overall_credibility_score",
    ai_result.get(
        "credibility_score",
        calculate_credibility_score(patterns)
    )
)

    db_analysis = AnalysisResult(
        url=url,
        domain=domain,
        credibility_score=float(credibility_score),
        total_patterns_found=len(patterns),
        page_title=str(ai_result.get("page_title", domain))[:500],
        industry_category=str(ai_result.get("industry_category", "unknown"))[:100],
        analysis_duration_seconds=duration
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    for pattern in patterns:
        db_pattern = DetectedPattern(
            analysis_id=db_analysis.id,
            pattern_type=str(pattern.get("pattern_type", "unknown"))[:100],
            pattern_name=str(pattern.get("pattern_name", "Unknown Pattern"))[:200],
            severity=str(pattern.get("severity", "Low"))[:20],
            description=str(pattern.get("user_impact", ""))[:1000],
            evidence=str(pattern.get("evidence", ""))[:1000],
            location_hint=str(pattern.get("location_hint", ""))[:500],
            confidence_score=float(pattern.get("confidence_score", 0.5))
        )
        db.add(db_pattern)

    db.commit()
    return db_analysis, credibility_score


@router.post("/url")
async def analyze_url(request: URLAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze a website URL for dark patterns"""

    start_time = time.time()
    url = request.url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    scraped = await scrape_website(url)

    if scraped.get("error") and not scraped.get("content"):
        raise HTTPException(
            status_code=400,
            detail=f"Could not access website: {scraped['error']}"
        )

    content_to_analyze = scraped.get("content", "")

    domain = extract_domain(url)

    # Temporary reference/demo mode
    if DEMO_MODE and domain in DEMO_RESULTS:
        ai_result = DEMO_RESULTS[domain]
    else:
        ai_result = await analyze_with_gemini(
            content_to_analyze,
            url
        )

    patterns = ai_result.get("dark_patterns", [])

    duration = round(
        time.time() - start_time,
        2
    )

    db_analysis, credibility_score = save_analysis(
        db,
        url,
        domain,
        ai_result,
        patterns,
        duration
    )

    return {
        "analysis_id": db_analysis.id,
        "url": url,
        "domain": domain,
        "page_title": ai_result.get("page_title", domain),
        "industry_category": ai_result.get(
            "industry_category",
            "unknown"
        ),
        "credibility_score": credibility_score,
        "credibility_label": get_severity_label(
            float(credibility_score)
        ),
        "total_patterns_found": len(patterns),
        "dark_patterns": patterns,
        "positive_practices": ai_result.get(
            "positive_practices",
            []
        ),
        "recommendations": ai_result.get(
            "recommendations",
            []
        ),
        "summary": ai_result.get(
            "summary",
            "Analysis complete."
        ),
        "analysis_duration_seconds": duration
    }


@router.post("/text")
async def analyze_text(request: TextAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze pasted text/HTML content for dark patterns"""
    start_time = time.time()

    if len(request.content.strip()) < 30:
        raise HTTPException(
            status_code=400,
            detail="Content too short. Please paste at least 30 characters."
        )

    url = request.url or "manual-input"
    domain = extract_domain(url) if url != "manual-input" else "manual-input"

    ai_result = await analyze_text_content(request.content, url)

    patterns = ai_result.get("dark_patterns", [])
    duration = round(time.time() - start_time, 2)

    db_analysis, credibility_score = save_analysis(db, url, domain, ai_result, patterns, duration)

    return {
        "analysis_id": db_analysis.id,
        "url": url,
        "domain": domain,
        "page_title": ai_result.get("page_title", domain),
        "industry_category": ai_result.get("industry_category", "unknown"),
        "credibility_score": credibility_score,
        "credibility_label": get_severity_label(float(credibility_score)),
        "total_patterns_found": len(patterns),
        "dark_patterns": patterns,
        "positive_practices": ai_result.get("positive_practices", []),
        "recommendations": ai_result.get("recommendations", []),
        "summary": ai_result.get("summary", "Analysis complete."),
        "analysis_duration_seconds": duration
    }


@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """Get recent analysis history"""
    results = db.query(AnalysisResult)\
        .order_by(AnalysisResult.analysis_date.desc())\
        .offset(skip).limit(limit).all()

    return [
        {
            "id": r.id,
            "url": r.url,
            "domain": r.domain,
            "credibility_score": r.credibility_score,
            "total_patterns_found": r.total_patterns_found,
            "industry_category": r.industry_category,
            "analysis_date": r.analysis_date.isoformat() if r.analysis_date else None
        }
        for r in results
    ]


@router.get("/{analysis_id}")
async def get_analysis_detail(analysis_id: int, db: Session = Depends(get_db)):
    """Get full details of a specific analysis"""
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    patterns = db.query(DetectedPattern)\
        .filter(DetectedPattern.analysis_id == analysis_id).all()

    return {
        "analysis": {
            "id": analysis.id,
            "url": analysis.url,
            "domain": analysis.domain,
            "credibility_score": analysis.credibility_score,
            "total_patterns_found": analysis.total_patterns_found,
            "page_title": analysis.page_title,
            "industry_category": analysis.industry_category,
            "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None
        },
        "patterns": [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "pattern_name": p.pattern_name,
                "severity": p.severity,
                "evidence": p.evidence,
                "location_hint": p.location_hint,
                "confidence_score": p.confidence_score
            }
            for p in patterns
        ]
    }
