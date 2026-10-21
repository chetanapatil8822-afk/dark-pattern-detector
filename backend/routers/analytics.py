from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, distinct
from backend.utils.db import get_db
from backend.models.models import AnalysisResult, DetectedPattern, CommunityReport
from datetime import datetime, timedelta

import os

from backend.services.spark_analytics import get_bda_summary

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(db: Session = Depends(get_db)):
    """Get overall analytics summary for dashboard"""

    total_analyses = db.query(func.count(AnalysisResult.id)).scalar() or 0
    total_patterns = db.query(func.count(DetectedPattern.id)).scalar() or 0
    total_community = db.query(func.count(CommunityReport.id)).scalar() or 0
    avg_score = db.query(func.avg(AnalysisResult.credibility_score)).scalar()
    unique_domains = db.query(func.count(distinct(AnalysisResult.domain))).scalar() or 0

    # Most common pattern type
    common_pattern = db.query(
        DetectedPattern.pattern_type,
        func.count(DetectedPattern.id).label("count")
    ).group_by(DetectedPattern.pattern_type)\
     .order_by(desc("count")).first()

    # Pattern severity breakdown
    severity_counts = db.query(
        DetectedPattern.severity,
        func.count(DetectedPattern.id).label("count")
    ).group_by(DetectedPattern.severity).all()

    # Industry breakdown
    industry_counts = db.query(
        AnalysisResult.industry_category,
        func.count(AnalysisResult.id).label("count")
    ).group_by(AnalysisResult.industry_category)\
     .order_by(desc("count")).limit(6).all()

    # Last 7 days trend
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_analyses = db.query(
        func.date(AnalysisResult.analysis_date).label("date"),
        func.count(AnalysisResult.id).label("count")
    ).filter(AnalysisResult.analysis_date >= seven_days_ago)\
     .group_by(func.date(AnalysisResult.analysis_date))\
     .order_by("date").all()

    # Pattern type distribution
    pattern_type_dist = db.query(
        DetectedPattern.pattern_type,
        func.count(DetectedPattern.id).label("count")
    ).group_by(DetectedPattern.pattern_type)\
     .order_by(desc("count")).limit(10).all()

    return {
        "totals": {
            "analyses": total_analyses,
            "patterns_detected": total_patterns,
            "community_reports": total_community,
            "unique_domains": unique_domains,
            "avg_credibility_score": round(avg_score, 1) if avg_score else 0
        },
        "most_common_pattern": common_pattern.pattern_type if common_pattern else "N/A",
        "severity_breakdown": [
            {"severity": s.severity, "count": s.count}
            for s in severity_counts
        ],
        "industry_breakdown": [
            {"industry": i.industry_category or "Unknown", "count": i.count}
            for i in industry_counts
        ],
        "daily_trend": [
            {"date": str(d.date), "count": d.count}
            for d in daily_analyses
        ],
        "pattern_type_distribution": [
            {
                "pattern_type": p.pattern_type.replace("_", " ").title(),
                "count": p.count
            }
            for p in pattern_type_dist
        ]
    }


@router.get("/credibility-distribution")
async def get_credibility_distribution(db: Session = Depends(get_db)):
    """Get distribution of credibility scores across all analyses"""

    all_scores = db.query(AnalysisResult.credibility_score)\
        .filter(AnalysisResult.credibility_score.isnot(None)).all()

    scores = [s.credibility_score for s in all_scores]

    distribution = {
        "dangerous": len([s for s in scores if s < 40]),
        "suspicious": len([s for s in scores if 40 <= s < 60]),
        "caution": len([s for s in scores if 60 <= s < 80]),
        "safe": len([s for s in scores if s >= 80])
    }

    return {
        "distribution": distribution,
        "total": len(scores),
        "average": round(sum(scores) / len(scores), 1) if scores else 0
    }


@router.get("/top-patterns")
async def get_top_patterns(limit: int = 5, db: Session = Depends(get_db)):
    """Get the most frequently detected dark patterns"""

    patterns = db.query(
        DetectedPattern.pattern_type,
        DetectedPattern.pattern_name,
        func.count(DetectedPattern.id).label("frequency"),
        func.avg(DetectedPattern.confidence_score).label("avg_confidence")
    ).group_by(
        DetectedPattern.pattern_type,
        DetectedPattern.pattern_name
    ).order_by(desc("frequency")).limit(limit).all()

    return [
        {
            "pattern_type": p.pattern_type,
            "pattern_name": p.pattern_name,
            "frequency": p.frequency,
            "avg_confidence": round(p.avg_confidence, 2) if p.avg_confidence else 0
        }
        for p in patterns
    ]

@router.get("/bda")
async def get_bda_analytics():
    """
    Run PySpark-based Big Data analytics
    on the dark pattern analysis database.
    """

    # Project root -> darkpattern.db
    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    db_path = os.path.join(
        project_root,
        "darkpattern.db"
    )

    if not os.path.exists(db_path):
        return {
            "error": "darkpattern.db not found",
            "db_path": db_path
        }

    try:
        bda_result = get_bda_summary(db_path)

        return {
            "status": "success",
            "engine": "PySpark",
            "database": "darkpattern.db",
            "data": bda_result
        }

    except Exception as e:
        return {
            "status": "error",
            "engine": "PySpark",
            "error": str(e)
        }