import sys

import httpx
from django.conf import settings

from ..services import MedicalRecordRepository, serialize_medical_record
from .exceptions import MedicalSourceConfigError, MedicalSourceUnavailable
from .normalize import first_text, gender_from_value, parse_birth_date


def _empty_record():
    return {
        "found": False,
        "unavailable": False,
        "source": "",
        "full_name": "",
        "birth_date": None,
        "gender": "",
        "city": "",
        "clinic": "",
        "diagnosis": "",
    }


class OfficialMedicalAdapter:
    name = "official"

    def lookup(self, iin):
        base_url = getattr(settings, "MEDICAL_SOURCE_URL", "") or ""
        if not base_url:
            raise MedicalSourceConfigError(
                "MEDICAL_SOURCE_URL не задан. Укажите DamuMed/eGov или официальный stage/sandbox."
            )
        url = base_url.rstrip("/")
        endpoint = url if url.endswith("/lookup") else f"{url}/lookup"
        try:
            response = httpx.post(endpoint, json={"iin": iin}, timeout=10.0)
        except httpx.HTTPError as exc:
            raise MedicalSourceUnavailable() from exc
        if response.status_code == 404:
            record = _empty_record()
            record["source"] = self.name
            return record
        if response.status_code >= 400:
            raise MedicalSourceUnavailable()
        payload = response.json() if response.content else {}
        return self._map_payload(payload)

    def _map_payload(self, payload):
        diagnoses = payload.get("diagnoses") or []
        first_diagnosis = diagnoses[0] if diagnoses else None
        diagnosis_from_list = ""
        if isinstance(first_diagnosis, dict):
            diagnosis_from_list = first_diagnosis.get("name") or ""
        elif isinstance(first_diagnosis, str):
            diagnosis_from_list = first_diagnosis
        diagnosis = first_text(
            payload.get("diagnosis"),
            payload.get("diagnosis_name"),
            diagnosis_from_list,
        )
        birth_date = parse_birth_date(
            payload.get("birth_date") or payload.get("birthDate") or payload.get("date_of_birth")
        )
        return {
            "found": True,
            "unavailable": False,
            "source": self.name,
            "full_name": first_text(payload.get("full_name"), payload.get("fullName"), payload.get("fio")),
            "birth_date": birth_date.isoformat() if birth_date else None,
            "gender": gender_from_value(payload.get("gender") or payload.get("sex")),
            "city": first_text(payload.get("city"), payload.get("locality")),
            "clinic": first_text(
                payload.get("clinic"),
                payload.get("organization"),
                payload.get("medical_org"),
            ),
            "diagnosis": diagnosis,
        }


class DevMedregistryAdapter:
    name = "dev"

    def lookup(self, iin):
        if not self._allowed():
            raise MedicalSourceConfigError("Dev medical adapter is not allowed in production")
        record = MedicalRecordRepository().get_by_iin(iin)
        if record is None:
            result = _empty_record()
            result["source"] = self.name
            return result
        serialized = serialize_medical_record(record)
        return {
            "found": True,
            "unavailable": False,
            "source": self.name,
            "full_name": serialized.get("full_name") or "",
            "birth_date": serialized.get("birth_date"),
            "gender": serialized.get("gender") or "",
            "city": serialized.get("city") or "",
            "clinic": serialized.get("clinic") or "",
            "diagnosis": serialized.get("diagnosis") or "",
        }

    def _allowed(self):
        if getattr(settings, "DEBUG", False):
            return True
        return "test" in sys.argv


def get_medical_adapter():
    name = getattr(settings, "MEDICAL_SOURCE_ADAPTER", "official")
    if name == "dev":
        adapter = DevMedregistryAdapter()
        if not adapter._allowed():
            raise MedicalSourceConfigError("Dev medical adapter is not allowed in production")
        return adapter
    return OfficialMedicalAdapter()
