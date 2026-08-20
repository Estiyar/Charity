from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken

from .ecp.exceptions import EcpConfigError, EcpVerificationError
from .ecp.service import serialize_verification, verify_cms
from .models import EcpVerification


class InternalEcpVerifyView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        challenge = request.data.get("challenge")
        cms = request.data.get("cms")
        try:
            record, iin = verify_cms(challenge, cms)
        except EcpConfigError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except EcpVerificationError as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)
        payload = serialize_verification(record)
        payload["iin"] = iin
        return Response(payload, status=status.HTTP_201_CREATED)


class InternalEcpVerificationView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        record = EcpVerification.objects.filter(pk=pk).first()
        if record is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        include_iin = request.query_params.get("reveal") == "1"
        return Response(serialize_verification(record, include_iin=include_iin, request=request))
