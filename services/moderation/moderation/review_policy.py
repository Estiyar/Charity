from ekomek_common.constants import UserStatus

from .models import ManualReviewCase

COMMENT_REQUIRED_ACTIONS = {"reject", "request_revision"}
DEFAULT_EVIDENCE = [
    "risk_score",
    "risk_level",
    "risk_reasons",
    "verification_snapshot",
    "duplicate_signals",
    "document_metadata",
    "previous_decisions",
]

ACTION_CASE_STATUS = {
    "approve": ManualReviewCase.Status.APPROVED,
    "reject": ManualReviewCase.Status.REJECTED,
    "request_revision": ManualReviewCase.Status.REVISION_REQUIRED,
    "suspend": ManualReviewCase.Status.SUSPENDED,
}


def allowed_actions(case):
    if case.status in (ManualReviewCase.Status.OPEN, ManualReviewCase.Status.REVISION_REQUIRED):
        return ["approve", "reject", "request_revision", "suspend"]
    if case.status == ManualReviewCase.Status.SUSPENDED:
        return ["unsuspend", "reject"]
    if case.status == ManualReviewCase.Status.APPROVED:
        return ["suspend"]
    return []


def case_status_after_unsuspend(previous_status):
    restored = previous_status or ""
    if restored in ("active", UserStatus.ACTIVE, UserStatus.ECP_VERIFIED, "approved"):
        return ManualReviewCase.Status.APPROVED
    return ManualReviewCase.Status.OPEN


def approved_user_status(user):
    if user.get("ecp_verification_id"):
        return UserStatus.ECP_VERIFIED
    return UserStatus.ACTIVE
