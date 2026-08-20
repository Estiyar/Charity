class Role:
    DONOR = "donor"
    AUTHOR = "author"
    MODERATOR = "moderator"
    ADMIN = "admin"
    ALL = (DONOR, AUTHOR, MODERATOR, ADMIN)
    PUBLIC_REGISTER = (DONOR, AUTHOR)
    STAFF = (MODERATOR, ADMIN)


class UserStatus:
    ACTIVE = "active"
    UNVERIFIED = "unverified"
    ECP_VERIFIED = "ecp_verified"
    MANUAL_REVIEW = "manual_review"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    ALL = (ACTIVE, UNVERIFIED, ECP_VERIFIED, MANUAL_REVIEW, REJECTED, BLOCKED)
    CAN_LOGIN = (ACTIVE, UNVERIFIED, ECP_VERIFIED, MANUAL_REVIEW)
    CAN_CREATE_FUNDRAISER = (ACTIVE, ECP_VERIFIED)


class RelationshipType:
    SELF = "self"
    PARENT = "parent"
    GUARDIAN = "guardian"
    REPRESENTATIVE = "representative"
    ALL = (SELF, PARENT, GUARDIAN, REPRESENTATIVE)
    DEPENDENT = (PARENT, GUARDIAN)
    OTHER = (REPRESENTATIVE,)


class RepresentationMethod:
    ECP = "ecp"
    DOCUMENT = "document"
    EXTERNAL_SOURCE = "external_source"
    MANUAL_REVIEW = "manual_review"
    ALL = (ECP, DOCUMENT, EXTERNAL_SOURCE, MANUAL_REVIEW)


class RepresentationStatus:
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    ALL = (PENDING, VERIFIED, REJECTED, MANUAL_REVIEW)


class BeneficiaryStatus:
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    INCOMPLETE = "incomplete"
    MANUAL_REVIEW = "manual_review"
    ALL = (UNVERIFIED, VERIFIED, INCOMPLETE, MANUAL_REVIEW)


class CardStatus:
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    MANUAL_REVIEW = "manual_review"
    REVISION_REQUIRED = "revision_required"
    APPROVED = "approved"
    ACTIVE = "active"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    DECEASED = "deceased"
    REDISTRIBUTION = "redistribution"
    ARCHIVED = "archived"
    ALL = (
        DRAFT,
        PENDING_MODERATION,
        MANUAL_REVIEW,
        REVISION_REQUIRED,
        APPROVED,
        ACTIVE,
        REJECTED,
        SUSPENDED,
        COMPLETED,
        DECEASED,
        REDISTRIBUTION,
        ARCHIVED,
    )


PUBLIC_CARD_STATUSES = {CardStatus.ACTIVE, CardStatus.COMPLETED, CardStatus.REDISTRIBUTION}
VIEWABLE_PUBLIC_STATUSES = PUBLIC_CARD_STATUSES | {CardStatus.SUSPENDED}
EDITABLE_CARD_STATUSES = {CardStatus.DRAFT, CardStatus.REVISION_REQUIRED}
DOCUMENT_UPLOAD_STATUSES = {CardStatus.DRAFT, CardStatus.REVISION_REQUIRED, CardStatus.ACTIVE}
POST_ACTIVATION_STATUSES = {CardStatus.ACTIVE, CardStatus.COMPLETED, CardStatus.REDISTRIBUTION, CardStatus.APPROVED}
EXPENSE_CARD_STATUSES = {CardStatus.ACTIVE, CardStatus.COMPLETED}
DONATABLE_STATUSES = {CardStatus.ACTIVE}
ACTIVE_FUNDRAISER_STATUSES = {
    CardStatus.DRAFT,
    CardStatus.PENDING_MODERATION,
    CardStatus.MANUAL_REVIEW,
    CardStatus.REVISION_REQUIRED,
    CardStatus.APPROVED,
    CardStatus.ACTIVE,
    CardStatus.SUSPENDED,
}
MODERATION_LIST_STATUSES = {
    CardStatus.PENDING_MODERATION,
    CardStatus.MANUAL_REVIEW,
    CardStatus.REVISION_REQUIRED,
    CardStatus.APPROVED,
    CardStatus.ACTIVE,
    CardStatus.REJECTED,
    CardStatus.SUSPENDED,
}

CARD_TRANSITIONS = {
    CardStatus.DRAFT: {CardStatus.PENDING_MODERATION, CardStatus.MANUAL_REVIEW},
    CardStatus.PENDING_MODERATION: {
        CardStatus.APPROVED,
        CardStatus.REVISION_REQUIRED,
        CardStatus.REJECTED,
        CardStatus.MANUAL_REVIEW,
        CardStatus.SUSPENDED,
    },
    CardStatus.MANUAL_REVIEW: {
        CardStatus.APPROVED,
        CardStatus.REVISION_REQUIRED,
        CardStatus.REJECTED,
        CardStatus.PENDING_MODERATION,
        CardStatus.SUSPENDED,
    },
    CardStatus.REVISION_REQUIRED: {
        CardStatus.PENDING_MODERATION,
        CardStatus.MANUAL_REVIEW,
        CardStatus.SUSPENDED,
    },
    CardStatus.APPROVED: {CardStatus.ACTIVE, CardStatus.SUSPENDED, CardStatus.MANUAL_REVIEW},
    CardStatus.ACTIVE: {
        CardStatus.COMPLETED,
        CardStatus.DECEASED,
        CardStatus.REDISTRIBUTION,
        CardStatus.ARCHIVED,
        CardStatus.SUSPENDED,
        CardStatus.MANUAL_REVIEW,
        CardStatus.REVISION_REQUIRED,
        CardStatus.PENDING_MODERATION,
    },
    CardStatus.SUSPENDED: {
        CardStatus.ACTIVE,
        CardStatus.MANUAL_REVIEW,
        CardStatus.REVISION_REQUIRED,
        CardStatus.PENDING_MODERATION,
        CardStatus.REJECTED,
        CardStatus.ARCHIVED,
    },
    CardStatus.COMPLETED: {CardStatus.REDISTRIBUTION, CardStatus.ARCHIVED, CardStatus.MANUAL_REVIEW},
    CardStatus.DECEASED: {CardStatus.REDISTRIBUTION, CardStatus.ARCHIVED},
    CardStatus.REDISTRIBUTION: {CardStatus.ARCHIVED, CardStatus.COMPLETED},
    CardStatus.REJECTED: {CardStatus.ARCHIVED},
    CardStatus.ARCHIVED: set(),
}


class InvalidStatusTransition(Exception):
    pass


def can_transition(current, target):
    return target in CARD_TRANSITIONS.get(current, set())


def next_status(current, target):
    if not can_transition(current, target):
        raise InvalidStatusTransition(f"Нельзя перейти из '{current}' в '{target}'")
    return target


EVENT_SUBSCRIPTIONS = {
    "user.registered": ["profile", "moderation", "notifications", "admin"],
    "user.manual_review_required": ["moderation", "notifications", "admin"],
    "user.status_changed": ["moderation", "notifications", "admin"],
    "ecp.verified": ["identity", "profile", "admin"],
    "user.blocked": ["cards", "notifications", "admin"],
    "user.role_changed": ["admin"],
    "user.updated": ["profile", "admin"],
    "profile.updated": ["cards", "admin"],
    "card.created": ["moderation", "notifications", "admin"],
    "card.submitted": ["moderation", "notifications"],
    "card.manual_review_required": ["moderation", "notifications", "admin"],
    "card.duplicate_detected": ["moderation", "notifications", "admin"],
    "card.status_changed": ["payments", "moderation", "notifications", "admin"],
    "card.revision_required": ["notifications"],
    "card.suspended": ["payments", "notifications", "admin"],
    "card.unsuspended": ["notifications", "admin"],
    "report.created": ["moderation", "cards", "notifications", "admin"],
    "report.resolved": ["notifications", "admin"],
    "document.uploaded": ["cards", "moderation"],
    "document.verified": ["cards", "moderation"],
    "document.rejected": ["cards", "moderation"],
    "document.expired": ["cards", "moderation", "notifications"],
    "document.revision_required": ["notifications"],
    "beneficiary.created": ["cards", "admin"],
    "beneficiary.updated": ["cards", "admin"],
    "representation.verified": ["cards", "moderation", "admin"],
    "representation.submitted": ["moderation", "notifications", "admin"],
    "representation.rejected": ["cards", "notifications", "admin"],
    "payment.created": ["notifications"],
    "payment.succeeded": ["cards", "notifications", "expenses"],
    "payment.failed": ["notifications"],
    "expense.created": ["moderation", "notifications"],
    "expense.submitted": ["moderation", "notifications"],
    "expense.approved": ["cards", "notifications"],
    "expense.rejected": ["notifications"],
    "expense.revision_required": ["notifications"],
    "expense.totals_changed": ["cards"],
    "invoice.created": ["moderation", "notifications"],
    "invoice.verified": ["moderation", "notifications"],
    "invoice.rejected": ["notifications"],
    "payout.requested": ["notifications"],
    "payout.succeeded": ["cards", "notifications"],
    "payout.failed": ["notifications"],
    "redistribution.choice_applied": ["expenses", "notifications"],
    "moderation.decision_created": ["cards", "notifications", "admin"],
    "review.opened": ["notifications", "admin"],
    "review.decision_applied": ["cards", "identity", "notifications", "admin"],
    "notification.requested": ["notifications"],
}

SERVICE_QUEUES = {
    "identity": "identity.events",
    "profile": "profile.events",
    "cards": "cards.events",
    "verification": "verification.events",
    "documents": "documents.events",
    "payments": "payments.events",
    "moderation": "moderation.events",
    "expenses": "expenses.events",
    "notifications": "notifications.events",
    "admin": "admin.events",
}
