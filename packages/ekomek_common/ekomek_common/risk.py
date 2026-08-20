class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    ALL = (LOW, MEDIUM, HIGH, CRITICAL)
    CHOICES = [(item, item) for item in ALL]


DEFAULT_RISK_FACTOR_WEIGHTS = {
    "new_account": 10,
    "missing_documents": 15,
    "unverified_documents": 10,
    "duplicate_beneficiary": 15,
    "duplicate_card": 25,
    "reused_payout_details": 20,
    "high_volume_author": 10,
    "high_volume_device_ip": 10,
    "critical_data_change": 15,
    "substantiated_reports": 20,
    "external_source_discrepancy": 15,
    "suspicious_payment_behavior": 20,
    "fraud_list_match": 40,
    "stolen_photos_report": 35,
}

DEFAULT_RISK_THRESHOLDS = {
    "low_max": 25,
    "medium_max": 55,
    "high_max": 80,
}

DEFAULT_BUSINESS_LIMITS = {
    "max_fundraisers_per_author_per_month": 2,
    "max_fundraisers_per_author_total_active": 1,
    "beneficiary_change_after_activation_forbidden": True,
    "target_amount_change_requires_remoderation": True,
    "clinic_change_requires_reverification": True,
    "payout_change_requires_reverification": True,
    "conflicting_document_uploads_threshold": 3,
}

RISK_CONFIG_VERSION = "1.0"


def risk_level_from_score(score, thresholds=None):
    thresholds = thresholds or DEFAULT_RISK_THRESHOLDS
    if score <= thresholds.get("low_max", 25):
        return RiskLevel.LOW
    if score <= thresholds.get("medium_max", 55):
        return RiskLevel.MEDIUM
    if score <= thresholds.get("high_max", 80):
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL
