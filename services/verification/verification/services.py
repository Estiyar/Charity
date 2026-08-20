from datetime import date

from ekomek_common.crypto import hmac_hash

from .models import FraudProfile, MedicalRecord

BLOCK_THRESHOLD = 70
REVIEW_THRESHOLD = 40


class MedicalRecordRepository:
    def get_by_hash(self, iin_hash):
        if not iin_hash:
            return None
        return MedicalRecord.objects.prefetch_related("diagnoses").filter(iin_hash=iin_hash).first()

    def get_by_iin(self, iin):
        return self.get_by_hash(hmac_hash(iin))


class FraudProfileRepository:
    def get_by_hash(self, iin_hash):
        if not iin_hash:
            return None
        return FraudProfile.objects.filter(iin_hash=iin_hash).first()

    def get_by_iin(self, iin):
        return self.get_by_hash(hmac_hash(iin))


def get_primary_diagnosis_name(record):
    diagnosis = record.diagnoses.order_by("-diagnosed_date").first()
    return diagnosis.name if diagnosis else ""


def calculate_age_from_birth_date(birth_date):
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def serialize_medical_record(record):
    return {
        "iin_hash": record.iin_hash,
        "iin_masked": record.iin_masked,
        "full_name": record.full_name,
        "birth_date": record.birth_date.isoformat(),
        "gender": record.gender,
        "city": record.city,
        "clinic": record.clinic,
        "age": calculate_age_from_birth_date(record.birth_date),
        "diagnosis": get_primary_diagnosis_name(record),
        "diagnoses": [
            {
                "name": item.name,
                "stage": item.stage,
                "diagnosed_date": item.diagnosed_date.isoformat(),
            }
            for item in record.diagnoses.all()
        ],
    }


def serialize_fraud_profile(profile):
    blocked = profile.risk_score >= BLOCK_THRESHOLD
    needs_review = REVIEW_THRESHOLD <= profile.risk_score < BLOCK_THRESHOLD
    return {
        "iin_hash": profile.iin_hash,
        "iin_masked": profile.iin_masked,
        "full_name": profile.full_name,
        "risk_score": profile.risk_score,
        "risk_level": profile.risk_level,
        "reasons": profile.reasons,
        "blocked": blocked,
        "needs_review": needs_review,
    }
