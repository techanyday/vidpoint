"""Payment configuration for VidPoint"""

# Subscription Plans
SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'monthly_summaries': 3,
        'features': [
            'Up to 200 tokens',
            'Word document export',
            'Basic support'
        ]
    },
    'starter': {
        'name': 'Starter',
        'price': 499,  # GHS 4.99
        'monthly_summaries': 50,
        'features': [
            'Up to 500 tokens',
            'Word document export',
            'Priority support',
            'Purchase additional credits'
        ]
    },
    'pro': {
        'name': 'Pro',
        'price': 999,  # GHS 9.99
        'monthly_summaries': 1000,
        'features': [
            'Up to 2,000 tokens',
            'Bulk processing',
            'Team accounts',
            'Premium support',
            'Purchase additional credits'
        ]
    }
}

# Credit Packages
CREDIT_PACKAGES = {
    'credits_500': {
        'name': 'Basic Pack',
        'summaries': 500,
        'price': 500,  # GHS 5.00
        'price_per_summary': 0.01  # GHS 0.01 per summary
    },
    'credits_1000': {
        'name': 'Value Pack',
        'summaries': 1000,
        'price': 1000,  # GHS 10.00
        'price_per_summary': 0.01  # GHS 0.01 per summary
    }
}

# Payment Methods
PAYMENT_METHODS = {
    'card': {
        'name': 'Credit/Debit Card',
        'description': 'Pay with Visa, Mastercard, or Verve',
        'enabled': True
    },
    'momo': {
        'name': 'Mobile Money',
        'description': 'Pay with MTN Mobile Money, Vodafone Cash, or AirtelTigo Money',
        'enabled': True,
        'providers': [
            {
                'id': 'mtn',
                'name': 'MTN Mobile Money',
                'logo': 'mtn-momo.png'
            },
            {
                'id': 'vodafone',
                'name': 'Vodafone Cash',
                'logo': 'vodafone-cash.png'
            },
            {
                'id': 'airteltigo',
                'name': 'AirtelTigo Money',
                'logo': 'airteltigo-money.png'
            }
        ]
    }
}
