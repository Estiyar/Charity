from datetime import timedelta

from django.utils import timezone

from ekomek_common.http import ServiceClientError, admin_client, verification_client
from ekomek_common.outbox import enqueue_event
from ekomek_common.risk import (
    DEFAULT_BUSINESS_LIMITS,
    DEFAULT_RISK_FACTOR_WEIGHTS,
    DEFAULT_RISK_THRESHOLDS,
    RISK_CONFIG_VERSION,
    RiskLevel,
    risk_level_from_score,
)

from .models import FundraisingCard
from .repositories import CardRepository
from .risk_models import RiskAssessment, RiskOverride


def _fetch_risk_config():
    try:
        return admin_client().get("/internal/risk-config/")
    except ServiceClientError:
        return None


def _active_weights():
    config = _fetch_risk_config()
    if config:
        merged = dict(DEFAULT_RISK_FACTOR_WEIGHTS)
        merged.update(config.get("factor_weights") or {})
        return merged, config.get("risk_thresholds") or DEFAULT_RISK_THRESHOLDS, config.get("version") or ""
    return dict(DEFAULT_RISK_FACTOR_WEIGHTS), dict(DEFAULT_RISK_THRESHOLDS), RISK_CONFIG_VERSION


def _fetch_fraud_score(iin_hash):
    if not iin_hash:
        return 0, []
    try:
        result = verification_client().get(f"/internal/antifraud/hash/{iin_hash}/")
    except ServiceClientError:
        return 0, []
    if result is None:
        return 0, []
    return int(result.get("risk_score") or 0), list(result.get("reasons") or [])


def _make_factor(code, weight, source, detail=""):
    return {
        "code": code,
        "weight": weight,
        "source": source,
        "detail": detail,
        "timestamp": timezone.now().isoformat(),
    }


def collect_risk_factors(card, weights=None, thresholds=None):
    if weights is None:
        weights, thresholds, _ = _active_weights()
    factors = []
    repo = CardRepository()

    fraud_score, fraud_reasons = _fetch_fraud_score(card.iin_hash)
    if fraud_score >= 40:
        factors.append(_make_factor("fraud_list_match", weights.get("fraud_list_match", 40), "antifraud", f"fraud_score={fraud_score}"))
    for reason in fraud_reasons:
        if "fraud" in str(reason).lower() and not any(f["code"] == "fraud_list_match" for f in factors):
            factors.append(_make_factor("fraud_list_match", weights.get("fraud_list_match", 40), "antifraud", str(reason)))

    if card.author_id:
        created_since = timezone.now() - timedelta(days=365)
        author_cards_count = FundraisingCard.objects.filter(
            author_id=card.author_id, created_at__gte=created_since
        ).exclude(pk=card.pk).count()
        if author_cards_count >= 3:
            factors.append(_make_factor("high_volume_author", weights.get("high_volume_author", 10), "volume_check", f"count={author_cards_count}"))

    if card.duplicate_suspected:
        for signal in card.duplicate_signals or []:
            code = signal.get("code") if isinstance(signal, dict) else str(signal)
            if code == "same_beneficiary_iin_hash":
                factors.append(_make_factor("duplicate_beneficiary", weights.get("duplicate_beneficiary", 15), "duplicate_check", signal.get("message", "") if isinstance(signal, dict) else ""))
            elif code == "active_fundraiser_same_beneficiary":
                factors.append(_make_factor("duplicate_card", weights.get("duplicate_card", 25), "duplicate_check"))
            elif code == "reused_payout_details":
                factors.append(_make_factor("reused_payout_details", weights.get("reused_payout_details", 20), "duplicate_check"))

    if card.report_risk_score and card.report_risk_score >= 20:
        factors.append(_make_factor("substantiated_reports", weights.get("substantiated_reports", 20), "user_reports", f"report_score={card.report_risk_score}"))

    review_reasons = card.review_reasons or []
    for reason in review_reasons:
        if "critical_change:" in str(reason):
            factors.append(_make_factor("critical_data_change", weights.get("critical_data_change", 15), "card_history", str(reason)))
            break

    return factors


def calculate_risk_score(card):
    weights, thresholds, config_version = _active_weights()
    factors = collect_risk_factors(card, weights, thresholds)
    raw_score = sum(factor["weight"] for factor in factors)
    score = min(raw_score, 100)
    level = risk_level_from_score(score, thresholds)

    existing = RiskAssessment.latest_for_card(card.id)
    if existing and existing.risk_score == score and existing.risk_level == level:
        return existing

    assessment = RiskAssessment.objects.create(
        card_id=card.id,
        risk_score=score,
        risk_level=level,
        factors=factors,
        config_version=config_version,
    )

    card.high_risk = level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    update_fields = ["high_risk", "updated_at"]
    if hasattr(card, "risk_score_cached"):
        card.risk_score_cached = score
        update_fields.append("risk_score_cached")
    card.save(update_fields=update_fields)

    return assessment


def override_risk(card_id, moderator, new_score, reason):
    card = FundraisingCard.objects.get(pk=card_id)
    existing = RiskAssessment.latest_for_card(card_id)
    old_score = existing.risk_score if existing else 0
    old_level = existing.risk_level if existing else RiskLevel.LOW

    _, thresholds, config_version = _active_weights()
    new_level = risk_level_from_score(new_score, thresholds)

    override = RiskOverride.objects.create(
        card_id=card_id,
        moderator_id=getattr(moderator, "id", 0),
        moderator_name=getattr(moderator, "full_name", "") or "",
        previous_score=old_score,
        previous_level=old_level,
        new_score=new_score,
        new_level=new_level,
        reason=reason,
    )

    RiskAssessment.objects.create(
        card_id=card_id,
        risk_score=new_score,
        risk_level=new_level,
        factors=[{
            "code": "moderator_override",
            "weight": new_score,
            "source": "moderator",
            "detail": reason,
            "timestamp": timezone.now().isoformat(),
        }],
        config_version=config_version,
    )

    card.high_risk = new_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    card.save(update_fields=["high_risk", "updated_at"])

    return override


def should_auto_suspend(assessment):
    return assessment.risk_level == RiskLevel.CRITICAL


def should_trigger_manual_review(assessment):
    return assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
