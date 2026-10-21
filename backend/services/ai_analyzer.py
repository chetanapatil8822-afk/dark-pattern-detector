import os
import json
import re
from typing import Dict, List, Any

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_AVAILABLE = False
genai = None

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print("✅ Gemini AI configured")
    except Exception as e:
        print(f"⚠️ Gemini setup error: {e}")
else:
    print("⚠️ GEMINI_API_KEY not set — local detector will be used")


# Use only the model that was actually available in your previous test.
MODEL_CANDIDATES = [
    "gemini-flash-latest"
]


SYSTEM_PROMPT = """
You are an expert UX researcher specializing in identifying dark patterns.

Analyze the supplied website content and identify dark patterns only when
there is evidence in the supplied content.

Dark pattern types:

1. fake_urgency — false countdown timers, fake deadlines, artificial urgency
2. hidden_costs — fees revealed late or unexpected charges
3. trick_questions — confusing questions or pre-selected choices
4. roach_motel — easy signup but difficult cancellation
5. misdirection — important information hidden or misleading visual/text emphasis
6. forced_continuity — free trial or subscription automatically renewing
7. social_proof_manipulation — fake viewers, fabricated popularity or reviews
8. confirm_shaming — guilt-tripping users for declining
9. disguised_ads — advertising presented as normal content
10. privacy_zuckering — confusing or excessive data-sharing consent

IMPORTANT:
- Do not invent evidence.
- Only report a pattern when the supplied content contains supporting evidence.
- If there is insufficient evidence, do not report the pattern.
- Confidence must represent confidence in the evidence.
- Return valid JSON only.
"""


# ============================================================
# MAIN GEMINI ANALYZER
# ============================================================

async def analyze_with_gemini(page_content: str, url: str) -> Dict[str, Any]:
    """
    Analyze website content using Gemini when available.
    If Gemini fails or quota is exceeded, use the local detector.
    """

    content = page_content[:8000] if page_content else ""

    # Try Gemini
    if GEMINI_AVAILABLE and GEMINI_API_KEY:
        for model_name in MODEL_CANDIDATES:
            try:
                import asyncio

                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT
                )

                result = await _run_gemini_prompt(
                    model,
                    content,
                    url
                )

                if result is not None:
                    print(
                        f"✅ Gemini analysis succeeded using model: "
                        f"{model_name}"
                    )

                    # Make sure score is valid
                    result = _normalize_result(result)

                    return result

            except Exception as e:
                print(
                    f"⚠️ Gemini model {model_name} failed: {e}"
                )

    # Gemini unavailable / quota exceeded
    print("⚠️ Gemini unavailable — using LOCAL dark-pattern detector")

    return _local_analysis(content, url)


# ============================================================
# GEMINI REQUEST
# ============================================================

async def _run_gemini_prompt(model, content: str, url: str):
    """
    Run Gemini request.
    Returns None if Gemini fails.
    """

    try:

        prompt = f"""
Analyze this website for dark patterns.

URL:
{url}

WEBSITE CONTENT:
{content}

Return ONLY this JSON structure:

{{
    "page_title": "page title or domain",
    "industry_category": "e-commerce or travel or subscription or food-delivery or social-media or finance or other",
    "overall_credibility_score": 75,
    "summary": "Short evidence-based assessment.",
    "dark_patterns": [
        {{
            "pattern_type": "fake_urgency",
            "pattern_name": "Descriptive name",
            "severity": "High",
            "confidence_score": 0.92,
            "evidence": "Exact text or element found in supplied content",
            "location_hint": "Where it was found",
            "user_impact": "Potential impact on users"
        }}
    ],
    "positive_practices": [],
    "recommendations": []
}}

Score guide:
80-100 = Safe
60-79 = Caution
40-59 = Suspicious
0-39 = Dangerous

Do not invent patterns or evidence.
Return ONLY JSON.
"""

        response = model.generate_content(prompt)

        if not response or not response.text:
            return None

        response_text = response.text.strip()

        # Remove markdown code fences
        if "```json" in response_text:
            response_text = (
                response_text
                .split("```json", 1)[1]
                .split("```", 1)[0]
                .strip()
            )

        elif "```" in response_text:
            response_text = (
                response_text
                .split("```", 1)[1]
                .split("```", 1)[0]
                .strip()
            )

        # Remove trailing commas before } or ]
        response_text = re.sub(
            r",\s*([}\]])",
            r"\1",
            response_text
        )

        result = json.loads(response_text)

        return result

    except Exception as e:
        print(f"⚠️ Gemini call error: {e}")
        return None


# ============================================================
# LOCAL DARK PATTERN DETECTOR
# ============================================================

def _local_analysis(content: str, url: str) -> Dict[str, Any]:
    """
    Local rule-based detector.

    This is NOT mock data.
    It analyzes the actual scraped website content.
    """

    text = content or ""
    lower_text = text.lower()

    patterns = []

    # --------------------------------------------------------
    # 1. FAKE URGENCY
    # --------------------------------------------------------

    urgency_patterns = [
        r"\b\d+\s*(minutes?|mins?|hours?|seconds?|secs?)\s*(left|remaining)\b",
        r"\bonly\s+\d+\s*(minutes?|hours?|items?|left)\b",
        r"\bending\s+(soon|today|tonight)\b",
        r"\bexpires?\s+(soon|today|tonight)\b",
        r"\blimited\s*time\b",
        r"\bact\s+now\b",
        r"\bhurry\b",
        r"\blast\s+chance\b",
        r"\bwhile\s+stocks?\s+last\b",
        r"\btime\s+left\b"
    ]

    urgency_match = _find_match(urgency_patterns, text)

    if urgency_match:
        patterns.append({
            "pattern_type": "fake_urgency",
            "pattern_name": "Urgency or Countdown Language",
            "severity": "High",
            "confidence_score": 0.82,
            "evidence": urgency_match,
            "location_hint": "Page content",
            "user_impact": (
                "Creates time pressure that may encourage users "
                "to make rushed decisions."
            )
        })

    # --------------------------------------------------------
    # 2. HIDDEN COSTS
    # --------------------------------------------------------

    cost_patterns = [
        r"convenience\s+fee",
        r"service\s+fee",
        r"processing\s+fee",
        r"handling\s+fee",
        r"platform\s+fee",
        r"packaging\s+fee",
        r"additional\s+fee",
        r"extra\s+charge",
        r"taxes?\s+and\s+fees",
        r"fees?\s+may\s+apply"
    ]

    cost_match = _find_match(cost_patterns, text)

    if cost_match:
        patterns.append({
            "pattern_type": "hidden_costs",
            "pattern_name": "Additional Fee Disclosure",
            "severity": "High",
            "confidence_score": 0.80,
            "evidence": cost_match,
            "location_hint": "Page content / pricing section",
            "user_impact": (
                "Users may not see the complete cost until later "
                "in the purchasing process."
            )
        })

    # --------------------------------------------------------
    # 3. TRICK QUESTIONS / PRESELECTED OPTIONS
    # --------------------------------------------------------

    trick_patterns = [
        r"pre[-\s]?selected",
        r"pre[-\s]?checked",
        r"\bchecked\s+by\s+default\b",
        r"\byes,\s*i\s+want\b",
        r"\bopt[-\s]?in\s+by\s+default\b",
        r"\bsubscribe\s+to\s+emails\b"
    ]

    trick_match = _find_match(trick_patterns, text)

    if trick_match:
        patterns.append({
            "pattern_type": "trick_questions",
            "pattern_name": "Pre-selected or Default Consent",
            "severity": "Medium",
            "confidence_score": 0.78,
            "evidence": trick_match,
            "location_hint": "Form / consent section",
            "user_impact": (
                "Users may unintentionally select an option "
                "without actively choosing it."
            )
        })

    # --------------------------------------------------------
    # 4. CONFIRM SHAMING
    # --------------------------------------------------------

    shaming_patterns = [
        r"no thanks.*save money",
        r"no,?\s*i\s+don'?t\s+want",
        r"i\s+don'?t\s+want\s+to\s+save",
        r"i\s+prefer\s+to\s+pay\s+more",
        r"no\s+thanks.*offer",
        r"decline.*deal"
    ]

    shaming_match = _find_match(shaming_patterns, text)

    if shaming_match:
        patterns.append({
            "pattern_type": "confirm_shaming",
            "pattern_name": "Guilt-Trip Decline Language",
            "severity": "Medium",
            "confidence_score": 0.80,
            "evidence": shaming_match,
            "location_hint": "Popup / promotional section",
            "user_impact": (
                "Uses emotionally loaded language to discourage "
                "users from declining an offer."
            )
        })

    # --------------------------------------------------------
    # 5. FORCED CONTINUITY
    # --------------------------------------------------------

    continuity_patterns = [
        r"free\s+trial.*auto",
        r"free\s+trial.*renew",
        r"automatically\s+renew",
        r"auto[-\s]?renew",
        r"subscription\s+will\s+renew",
        r"charged\s+after\s+trial"
    ]

    continuity_match = _find_match(
        continuity_patterns,
        text
    )

    if continuity_match:
        patterns.append({
            "pattern_type": "forced_continuity",
            "pattern_name": "Automatic Subscription Renewal",
            "severity": "High",
            "confidence_score": 0.84,
            "evidence": continuity_match,
            "location_hint": "Subscription / pricing section",
            "user_impact": (
                "Users may be charged automatically after a trial "
                "or subscription period."
            )
        })

    # --------------------------------------------------------
    # 6. SOCIAL PROOF MANIPULATION
    # --------------------------------------------------------

    social_patterns = [
        r"\d+\s+people\s+(are\s+)?viewing",
        r"\d+\s+people\s+(are\s+)?watching",
        r"\d+\s+people\s+bought",
        r"\d+\s+customers\s+are\s+viewing",
        r"\btrending\s+now\b",
        r"\bpopular\s+right\s+now\b",
        r"\bsold\s+\d+\s+today\b"
    ]

    social_match = _find_match(social_patterns, text)

    if social_match:
        patterns.append({
            "pattern_type": "social_proof_manipulation",
            "pattern_name": "Popularity or Viewer Pressure",
            "severity": "Medium",
            "confidence_score": 0.70,
            "evidence": social_match,
            "location_hint": "Product / content section",
            "user_impact": (
                "Popularity signals may pressure users into making "
                "faster decisions."
            )
        })

    # --------------------------------------------------------
    # 7. ROACH MOTEL
    # --------------------------------------------------------

    cancellation_patterns = [
        r"cancel.*difficult",
        r"contact\s+support.*cancel",
        r"cancellation\s+request",
        r"cancel\s+by\s+contacting",
        r"cannot\s+cancel\s+online",
        r"cancellation\s+process"
    ]

    cancellation_match = _find_match(
        cancellation_patterns,
        text
    )

    if cancellation_match:
        patterns.append({
            "pattern_type": "roach_motel",
            "pattern_name": "Difficult Cancellation Process",
            "severity": "High",
            "confidence_score": 0.72,
            "evidence": cancellation_match,
            "location_hint": "Account / subscription section",
            "user_impact": (
                "A complicated cancellation process can make it "
                "harder for users to leave a service."
            )
        })

    # --------------------------------------------------------
    # 8. MISDIRECTION
    # --------------------------------------------------------

    misdirection_patterns = [
        r"small\s+print",
        r"learn\s+more.*terms",
        r"terms\s+and\s+conditions",
        r"important\s+information",
        r"continue\s+without",
        r"skip\s+this\s+offer"
    ]

    misdirection_match = _find_match(
        misdirection_patterns,
        text
    )

    if misdirection_match:
        patterns.append({
            "pattern_type": "misdirection",
            "pattern_name": "Potentially Misleading Information Placement",
            "severity": "Low",
            "confidence_score": 0.55,
            "evidence": misdirection_match,
            "location_hint": "Page content",
            "user_impact": (
                "Important information may require additional attention "
                "or may be less prominent than the main action."
            )
        })

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = calculate_credibility_score(patterns)

    # --------------------------------------------------------
    # INDUSTRY
    # --------------------------------------------------------

    industry = detect_industry(lower_text)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if patterns:
        summary = (
            f"Local analysis detected {len(patterns)} potential "
            f"dark pattern(s) in the supplied website content. "
            f"The result is based on identifiable text signals "
            f"rather than a fixed demo response."
        )
    else:
        summary = (
            "No strong dark-pattern indicators were detected in "
            "the supplied website content using the local detection rules."
        )

    # --------------------------------------------------------
    # POSITIVE PRACTICES
    # --------------------------------------------------------

    positive = []

    if "privacy" in lower_text:
        positive.append("Privacy information is mentioned.")

    if "contact" in lower_text:
        positive.append("Contact information is visible.")

    if "return" in lower_text or "refund" in lower_text:
        positive.append("Return or refund information is available.")

    if "terms" in lower_text:
        positive.append("Terms and conditions are provided.")

    if not positive:
        positive.append(
            "No specific positive practice could be confidently "
            "verified from the extracted content."
        )

    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    recommendations = []

    for pattern in patterns:

        ptype = pattern["pattern_type"]

        if ptype == "fake_urgency":
            recommendations.append(
                "Use urgency messages only when they represent real "
                "deadlines or genuine stock conditions."
            )

        elif ptype == "hidden_costs":
            recommendations.append(
                "Display mandatory fees and additional charges clearly "
                "before the final checkout stage."
            )

        elif ptype == "trick_questions":
            recommendations.append(
                "Keep optional consent choices unselected by default."
            )

        elif ptype == "confirm_shaming":
            recommendations.append(
                "Use neutral language for both accept and decline actions."
            )

        elif ptype == "forced_continuity":
            recommendations.append(
                "Clearly disclose automatic renewal and provide "
                "an accessible cancellation option."
            )

        elif ptype == "social_proof_manipulation":
            recommendations.append(
                "Use transparent and verifiable popularity information."
            )

        elif ptype == "roach_motel":
            recommendations.append(
                "Provide a clear and accessible cancellation process."
            )

        elif ptype == "misdirection":
            recommendations.append(
                "Present important information clearly and prominently."
            )

    # Remove duplicate recommendations
    recommendations = list(dict.fromkeys(recommendations))

    if not recommendations:
        recommendations.append(
            "Continue monitoring the website for potentially "
            "misleading interface practices."
        )

    return {
        "page_title": extract_title(text, url),
        "industry_category": industry,
        "overall_credibility_score": score,
        "summary": summary,
        "dark_patterns": patterns,
        "positive_practices": positive,
        "recommendations": recommendations
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _find_match(patterns: List[str], text: str):
    """
    Find the first matching evidence phrase.
    """

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            # Return short readable evidence
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 100)

            evidence = text[start:end].replace("\n", " ").strip()

            return evidence

    return None


def detect_industry(text: str) -> str:

    if any(word in text for word in [
        "cart",
        "checkout",
        "add to cart",
        "product",
        "buy now",
        "shopping"
    ]):
        return "e-commerce"

    if any(word in text for word in [
        "flight",
        "hotel",
        "booking",
        "room",
        "travel"
    ]):
        return "travel"

    if any(word in text for word in [
        "subscription",
        "monthly plan",
        "annual plan",
        "free trial"
    ]):
        return "subscription"

    if any(word in text for word in [
        "delivery",
        "restaurant",
        "food order",
        "menu"
    ]):
        return "food-delivery"

    if any(word in text for word in [
        "followers",
        "likes",
        "share",
        "social"
    ]):
        return "social-media"

    if any(word in text for word in [
        "bank",
        "loan",
        "credit card",
        "investment",
        "finance"
    ]):
        return "finance"

    return "other"


def extract_title(content: str, url: str) -> str:

    match = re.search(
        r"\[TITLE\]\s*(.*?)(?:\n|$)",
        content,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    domain = (
        url
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    return domain


# ============================================================
# SCORE CALCULATION
# ============================================================

def calculate_credibility_score(
    patterns: List[Dict]
) -> float:

    if not patterns:
        return 95.0

    weights = {
        "Critical": 30,
        "High": 20,
        "Medium": 12,
        "Low": 5
    }

    deduction = 0.0

    for pattern in patterns:

        severity = pattern.get(
            "severity",
            "Low"
        )

        confidence = float(
            pattern.get(
                "confidence_score",
                0.5
            )
        )

        weight = weights.get(
            severity,
            5
        )

        deduction += weight * confidence

    return round(
        max(0.0, min(100.0, 100.0 - deduction)),
        1
    )


def get_severity_label(score: float) -> str:

    if score >= 80:
        return "Safe"

    if score >= 60:
        return "Caution"

    if score >= 40:
        return "Suspicious"

    return "Dangerous"


# ============================================================
# TEXT ANALYSIS
# ============================================================

async def analyze_text_content(
    text: str,
    url: str
) -> Dict[str, Any]:

    return await analyze_with_gemini(
        text,
        url
    )


# ============================================================
# NORMALIZE GEMINI RESULT
# ============================================================

def _normalize_result(
    result: Dict[str, Any]
) -> Dict[str, Any]:

    result.setdefault(
        "page_title",
        "Analyzed Website"
    )

    result.setdefault(
        "industry_category",
        "other"
    )

    result.setdefault(
        "dark_patterns",
        []
    )

    result.setdefault(
        "positive_practices",
        []
    )

    result.setdefault(
        "recommendations",
        []
    )

    result.setdefault(
        "summary",
        "Analysis completed."
    )

    # If Gemini returned patterns, calculate the score ourselves.
    # This avoids blindly trusting an arbitrary score returned by AI.
    patterns = result.get(
        "dark_patterns",
        []
    )

    if isinstance(patterns, list):
        result["overall_credibility_score"] = (
            calculate_credibility_score(patterns)
        )

    else:
        result["dark_patterns"] = []
        result["overall_credibility_score"] = 95.0

    return result