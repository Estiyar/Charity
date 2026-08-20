from ekomek_common.constants import ACTIVE_FUNDRAISER_STATUSES

from .duplicate_text import diagnoses_are_similar, purposes_are_similar

HARD_SIGNAL_CODES = frozenset(
    {
        "same_beneficiary_iin_hash",
        "active_fundraiser_same_beneficiary",
        "similar_diagnosis_purpose",
        "duplicate_document_number",
        "duplicate_document_file",
        "reused_payout_details",
    }
)
SOFT_SIGNAL_CODES = frozenset({"high_volume_author", "high_volume_fingerprint"})
AUTHOR_VOLUME_THRESHOLD = 3
FINGERPRINT_VOLUME_THRESHOLD = 3
SIGNAL_WEIGHTS = {
    "same_beneficiary_iin_hash": 15,
    "active_fundraiser_same_beneficiary": 25,
    "similar_diagnosis_purpose": 15,
    "duplicate_document_number": 20,
    "duplicate_document_file": 20,
    "reused_payout_details": 20,
    "high_volume_author": 10,
    "high_volume_fingerprint": 10,
}


def _ids_text(cards):
    return ", ".join(f"#{card.id}" for card in cards)


def _signal(code, cards, message):
    return {
        "code": code,
        "message": message,
        "matched_card_ids": [card.id for card in cards],
    }


def _safe_match(card, signal_codes):
    return {
        "card_id": card.id,
        "status": card.status,
        "iin_masked": card.iin_masked or "",
        "signal_codes": signal_codes,
    }


def _same_hash_cards(card, candidates, field_name):
    value = getattr(card, field_name, "") or ""
    if not value:
        return []
    return [item for item in candidates if getattr(item, field_name, "") == value]


def _similar_purpose_cards(card, candidates):
    if not card.diagnosis:
        return []
    matches = []
    for item in candidates:
        if not diagnoses_are_similar(card.diagnosis, item.diagnosis):
            continue
        if purposes_are_similar(card.description, item.description):
            matches.append(item)
    return matches


def collect_hard_signals(card, candidates, document_cards):
    signals = []
    same_iin = _same_hash_cards(card, candidates, "iin_hash")
    if same_iin:
        signals.append(
            _signal(
                "same_beneficiary_iin_hash",
                same_iin,
                f"Совпадает получатель с карточкой {_ids_text(same_iin)}.",
            )
        )
    active_same = [item for item in same_iin if item.status in ACTIVE_FUNDRAISER_STATUSES]
    if active_same:
        signals.append(
            _signal(
                "active_fundraiser_same_beneficiary",
                active_same,
                f"У получателя уже есть действующий сбор: карточка {_ids_text(active_same)}.",
            )
        )
    similar = _similar_purpose_cards(card, candidates)
    if similar:
        signals.append(
            _signal(
                "similar_diagnosis_purpose",
                similar,
                f"Похожие диагноз и цель с карточкой {_ids_text(similar)}.",
            )
        )
    same_document = _same_hash_cards(card, candidates, "document_number_hash")
    if same_document:
        signals.append(
            _signal(
                "duplicate_document_number",
                same_document,
                f"Совпадает номер документа с карточкой {_ids_text(same_document)}.",
            )
        )
    if document_cards:
        signals.append(
            _signal(
                "duplicate_document_file",
                document_cards,
                f"Совпадает файл документа с карточкой {_ids_text(document_cards)}.",
            )
        )
    same_payout = _same_hash_cards(card, candidates, "payout_details_hash")
    if same_payout:
        signals.append(
            _signal(
                "reused_payout_details",
                same_payout,
                f"Совпадают платёжные реквизиты с карточкой {_ids_text(same_payout)}.",
            )
        )
    return signals


def collect_soft_signals(author_cards, fingerprint_cards):
    signals = []
    if len(author_cards) >= AUTHOR_VOLUME_THRESHOLD:
        signals.append(
            _signal(
                "high_volume_author",
                author_cards[:10],
                "С аккаунта создано подозрительно много сборов.",
            )
        )
    if len(fingerprint_cards) >= FINGERPRINT_VOLUME_THRESHOLD:
        signals.append(
            _signal(
                "high_volume_fingerprint",
                fingerprint_cards[:10],
                "С одного устройства или IP создано подозрительно много сборов.",
            )
        )
    return signals


def build_matches(candidates, signals):
    codes_by_id = {}
    for signal in signals:
        for card_id in signal["matched_card_ids"]:
            codes_by_id.setdefault(card_id, []).append(signal["code"])
    matches = []
    seen = set()
    for card in candidates:
        if card.id in seen:
            continue
        codes = codes_by_id.get(card.id)
        if codes:
            matches.append(_safe_match(card, codes))
            seen.add(card.id)
    return matches


def risk_delta_for(signals):
    total = sum(SIGNAL_WEIGHTS.get(signal["code"], 0) for signal in signals)
    return min(total, 60)


def has_hard_duplicate(signals):
    return any(signal["code"] in HARD_SIGNAL_CODES for signal in signals)
