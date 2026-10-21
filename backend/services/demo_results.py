# Temporary reference/demo results for project presentation.
# Set DEMO_MODE = False later to return to the real analyzer.

DEMO_MODE = True


DEMO_RESULTS = {

    # ---------------------------------------------------------
    # AMAZON
    # FTC-documented Prime enrollment/cancellation case
    # ---------------------------------------------------------
    "amazon.com": {
        "page_title": "Amazon - Reference Demo",
        "industry_category": "e-commerce",

        # Reference/demo score
        "credibility_score": 75.0,
        "credibility_label": "Caution",
        "total_patterns_found": 2,

        "dark_patterns": [
            {
                "pattern_type": "forced_continuity",
                "pattern_name": "Subscription Trap / Forced Continuity",
                "severity": "High",
                "confidence_score": 0.95,
                "evidence": (
                    "FTC documented allegations concerning Prime enrollment "
                    "without adequate consumer consent and recurring subscription practices."
                ),
                "location_hint": "Prime enrollment flow",
                "user_impact": (
                    "Users may be enrolled into a recurring subscription "
                    "without fully understanding the commitment."
                )
            },
            {
                "pattern_type": "roach_motel",
                "pattern_name": "Difficult Cancellation",
                "severity": "High",
                "confidence_score": 0.96,
                "evidence": (
                    "FTC documented allegations that Amazon made cancellation "
                    "of Prime unnecessarily difficult."
                ),
                "location_hint": "Prime cancellation flow",
                "user_impact": (
                    "Users may face additional difficulty when attempting "
                    "to terminate a subscription."
                )
            }
        ],

        "summary": (
            "Reference-based result focused on documented concerns "
            "related to Amazon Prime enrollment and cancellation flows. "
            "This result does not indicate that the entire Amazon website "
            "is inherently deceptive."
        ),

        "positive_practices": [
            "Current settlement requires clearer Prime enrollment disclosures.",
            "Current settlement requires an easier cancellation method."
        ],

        "recommendations": [
            "Clearly disclose recurring subscription terms.",
            "Provide a straightforward cancellation process."
        ]
    },


    # ---------------------------------------------------------
    # BOOKS TO SCRAPE
    # Clean test website used for project demonstration
    # ---------------------------------------------------------
    "books.toscrape.com": {
        "page_title": "Books to Scrape",
        "industry_category": "e-commerce",
        "credibility_score": 94.0,
        "credibility_label": "Safe",
        "total_patterns_found": 0,

        "dark_patterns": [],

        "summary": (
            "No significant dark-pattern indicators were identified "
            "in this reference demonstration."
        ),

        "positive_practices": [
            "Product prices are directly displayed.",
            "Product information is clearly presented.",
            "Simple navigation structure."
        ],

        "recommendations": []
    },


    # ---------------------------------------------------------
    # QUOTES TO SCRAPE
    # Clean demonstration website
    # ---------------------------------------------------------
    "quotes.toscrape.com": {
        "page_title": "Quotes to Scrape",
        "industry_category": "other",
        "credibility_score": 97.0,
        "credibility_label": "Safe",
        "total_patterns_found": 0,

        "dark_patterns": [],

        "summary": (
            "No significant dark-pattern indicators were identified "
            "in this reference demonstration."
        ),

        "positive_practices": [
            "Simple page structure.",
            "No subscription flow.",
            "No forced purchase flow."
        ],

        "recommendations": []
    },


    # ---------------------------------------------------------
    # ABCMOUSE
    # FTC-documented difficult-cancellation case
    # ---------------------------------------------------------
    "abcmouse.com": {
        "page_title": "ABCmouse - Reference Demo",
        "industry_category": "subscription",
        "credibility_score": 48.0,
        "credibility_label": "Suspicious",
        "total_patterns_found": 1,

        "dark_patterns": [
            {
                "pattern_type": "roach_motel",
                "pattern_name": "Difficult Cancellation",
                "severity": "High",
                "confidence_score": 0.93,
                "evidence": (
                    "The FTC's dark-pattern report described allegations "
                    "that ABCmouse made cancellation of free trials and "
                    "subscription plans difficult despite promising easy cancellation."
                ),
                "location_hint": "Subscription cancellation flow",
                "user_impact": (
                    "Users may experience difficulty ending a subscription "
                    "after starting a trial or paid plan."
                )
            }
        ],

        "summary": (
            "Reference-based demonstration result based on an FTC-documented "
            "dark-pattern case involving subscription cancellation."
        ),

        "positive_practices": [],

        "recommendations": [
            "Make cancellation easy to locate.",
            "Allow users to cancel without unnecessary steps."
        ]
    }

}