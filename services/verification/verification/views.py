from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAuthor
from ekomek_common.validators import validate_iin

from .serializers import FraudProfileSerializer, MedicalRecordSerializer
from .services import (
    FraudProfileRepository,
    MedicalRecordRepository,
    serialize_fraud_profile,
    serialize_medical_record,
)


def _validated_iin(iin):
    try:
        validate_iin(iin)
    except DjangoValidationError as exc:
        return None, Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
    return iin, None


def _iin_from_body(request):
    return _validated_iin(request.data.get("iin"))


class MedicalRecordLookupView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]

    def post(self, request):
        iin, error = _iin_from_body(request)
        if error:
            return error
        record = MedicalRecordRepository().get_by_iin(iin)
        if record is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MedicalRecordSerializer(record).data)


class FraudProfileLookupView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]

    def post(self, request):
        iin, error = _iin_from_body(request)
        if error:
            return error
        profile = FraudProfileRepository().get_by_iin(iin)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FraudProfileSerializer(profile).data)


class InternalMedicalRecordLookupView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        iin, error = _iin_from_body(request)
        if error:
            return error
        record = MedicalRecordRepository().get_by_iin(iin)
        if record is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_medical_record(record))


class InternalFraudProfileLookupView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        iin, error = _iin_from_body(request)
        if error:
            return error
        profile = FraudProfileRepository().get_by_iin(iin)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_fraud_profile(profile))


class InternalMedicalRecordByHashView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, iin_hash):
        record = MedicalRecordRepository().get_by_hash(iin_hash)
        if record is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_medical_record(record))


class InternalFraudProfileByHashView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, iin_hash):
        profile = FraudProfileRepository().get_by_hash(iin_hash)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_fraud_profile(profile))
