from django.db import transaction

from ekomek_common.constants import CardStatus
from ekomek_common.http import ServiceClientError, cards_client
from ekomek_common.outbox import enqueue_event
from ekomek_common.reports import (
    REPORT_RISK_WEIGHTS,
    SERIOUS_REPORT_CATEGORIES,
    ReportStatus,
    reporter_key,
    request_reporter_fingerprint,
)

from .models import ModerationLog
from .report_models import ReportAttachment, UserReport
from .review_cases import open_card_review
from .services import ModerationActionError, fetch_card


class ReportActionError(Exception):
    pass


def _reporter_fingerprint(request):
    data = getattr(request, "data", None) or {}
    explicit = (data.get("reporter_fingerprint") or "").strip()
    return request_reporter_fingerprint(request, explicit)


def calculate_report_risk(card_id):
    seen = set()
    score = 0
    for report in UserReport.objects.filter(card_id=card_id).order_by("created_at", "id"):
        key = report.reporter_key
        if not key or key in seen:
            continue
        seen.add(key)
        score += REPORT_RISK_WEIGHTS.get(report.category, 5)
    return min(100, score), len(seen)


def sync_card_report_risk(card_id):
    score, unique_count = calculate_report_risk(card_id)
    try:
        cards_client().post(
            f"/internal/cards/{card_id}/report-risk/",
            json={"report_risk_score": score, "unique_report_count": unique_count},
        )
    except ServiceClientError as exc:
        raise ReportActionError((exc.payload or {}).get("detail") or str(exc)) from exc
    return score, unique_count


def _maybe_auto_suspend(card_id, category):
    if category not in SERIOUS_REPORT_CATEGORIES:
        return
    card = fetch_card(card_id)
    if not card or card.get("status") != CardStatus.ACTIVE:
        return
    reason = f"Автоматическая приостановка по жалобе: {category}"
    try:
        cards_client().post(
            f"/internal/cards/{card_id}/suspend/",
            json={"reason": reason, "source": "report"},
        )
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or str(exc)
        if "already" not in detail.lower():
            raise ReportActionError(detail) from exc


@transaction.atomic
def create_user_report(*, card_id, category, description, request, attachments=None):
    card = fetch_card(card_id)
    if card is None:
        raise ReportActionError("Сбор не найден.")
    user = getattr(request, "user", None)
    user_id = user.id if getattr(user, "is_authenticated", False) else None
    fingerprint = _reporter_fingerprint(request)
    key = reporter_key(user_id, fingerprint)
    if not key:
        raise ReportActionError("Не удалось определить автора жалобы.")
    report = UserReport.objects.create(
        card_id=card_id,
        reporter_user_id=user_id,
        reporter_key=key,
        category=category,
        description=description.strip(),
    )
    for attachment in attachments or []:
        ReportAttachment.objects.create(
            report=report,
            file=attachment,
            file_name=getattr(attachment, "name", "") or "",
        )
    score, unique_count = sync_card_report_risk(card_id)
    _maybe_auto_suspend(card_id, category)
    if score >= 40:
        open_card_review(
            {
                "card_id": card_id,
                "status": card.get("status"),
                "full_name": card.get("full_name", ""),
                "needs_extra_review": True,
                "review_reasons": [f"user_reports:{unique_count}"],
            }
        )
    enqueue_event(
        "report.created",
        "report",
        report.id,
        {
            "report_id": report.id,
            "card_id": card_id,
            "category": category,
            "reporter_user_id": user_id,
            "reporter_key": key,
            "report_risk_score": score,
            "unique_report_count": unique_count,
        },
    )
    return report


def resolve_user_report(report_id, moderator, *, resolution, status):
    if status not in (ReportStatus.RESOLVED, ReportStatus.DISMISSED):
        raise ReportActionError("Недопустимый статус решения.")
    if not (resolution or "").strip():
        raise ReportActionError("Укажите текст решения.")
    with transaction.atomic():
        report = UserReport.objects.select_for_update().get(pk=report_id)
        if report.status in (ReportStatus.RESOLVED, ReportStatus.DISMISSED):
            return report
        report.status = status
        report.resolution = resolution.strip()
        report.reviewed_by = getattr(moderator, "id", None)
        report.reviewed_by_name = getattr(moderator, "full_name", "") or ""
        report.save(
            update_fields=["status", "resolution", "reviewed_by", "reviewed_by_name", "updated_at"]
        )
        ModerationLog.objects.create(
            card_id=report.card_id,
            card_name="",
            moderator_id=getattr(moderator, "id", None),
            moderator_name=getattr(moderator, "full_name", "") or "",
            action=f"report_{status}",
            comment=resolution.strip(),
        )
        enqueue_event(
            "report.resolved",
            "report",
            report.id,
            {
                "report_id": report.id,
                "card_id": report.card_id,
                "status": status,
                "moderator_id": getattr(moderator, "id", None),
                "reporter_user_id": report.reporter_user_id,
                "resolution": report.resolution,
            },
        )
        return report


def open_reports():
    return UserReport.objects.filter(status__in=ReportStatus.OPEN).order_by("-created_at")
