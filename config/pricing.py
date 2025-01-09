"""Pricing configuration for VidPoint."""

PRICING_PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "monthly_summaries": 3,
        "max_tokens": 200,
        "features": [
            "Word document export",
            "Basic support"
        ]
    },
    "starter": {
        "name": "Starter",
        "price": 4.99,
        "monthly_summaries": 50,
        "max_tokens": 500,
        "features": [
            "Word document export",
            "Priority email support",
            "No ads"
        ]
    },
    "pro": {
        "name": "Pro",
        "price": 9.99,
        "monthly_summaries": 1000,
        "max_tokens": 2000,
        "features": [
            "Word document export",
            "Bulk processing",
            "Team accounts",
            "Priority support",
            "API access"
        ]
    }
}

CREDIT_PACKAGES = {
    "small": {
        "name": "Small Credit Pack",
        "price": 5.00,
        "summaries": 500
    },
    "large": {
        "name": "Large Credit Pack",
        "price": 10.00,
        "summaries": 1000
    }
}
