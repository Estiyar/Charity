class ReportCategory:
    SUSPECTED_FRAUD = "suspected_fraud"
    INCORRECT_INFORMATION = "incorrect_information"
    STOLEN_PHOTOS = "stolen_photos"
    OUTDATED_FUNDRAISER = "outdated_fundraiser"
    DOCUMENT_ISSUE = "document_issue"
    OTHER = "other"
    ALL = (
        SUSPECTED_FRAUD,
        INCORRECT_INFORMATION,
        STOLEN_PHOTOS,
        OUTDATED_FUNDRAISER,
        DOCUMENT_ISSUE,
        OTHER,
    )
    CHOICES = [(item, item) for item in ALL]


SERIOUS_REPORT_CATEGORIES = frozenset({ReportCategory.SUSPECTED_FRAUD, ReportCategory.STOLEN_PHOTOS})

REPORT_RISK_WEIGHTS = {
    ReportCategory.SUSPECTED_FRAUD: 40,
    ReportCategory.STOLEN_PHOTOS: 35,
    ReportCategory.INCORRECT_INFORMATION: 15,
    ReportCategory.OUTDATED_FUNDRAISER: 10,
    ReportCategory.DOCUMENT_ISSUE: 20,
    ReportCategory.OTHER: 5,
}


class ReportStatus:
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ALL = (PENDING, UNDER_REVIEW, RESOLVED, DISMISSED)
    OPEN = (PENDING, UNDER_REVIEW)


def reporter_key(user_id=None, fingerprint=""):
    if user_id:
        return f"user:{user_id}"
    normalized = (fingerprint or "").strip()
    if normalized:
        return f"guest:{normalized}"
    return ""


def request_reporter_fingerprint(request, explicit=""):
    normalized = (explicit or "").strip()
    if normalized:
        return normalized[:240]
    headers = getattr(request, "headers", {}) or {}
    forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or ""
    remote = getattr(request, "META", {}).get("REMOTE_ADDR", "")
    user_agent = headers.get("User-Agent") or headers.get("user-agent") or ""
    source = forwarded.split(",")[0].strip() or remote
    return f"{source}:{user_agent}"[:240]
