from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken
from ekomek_common.validators import validate_iin

from .medical.service import verify_recipient


class InternalRecipientVerifyView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        iin = request.data.get("iin")
        try:
            validate_iin(iin)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        identity = {
            "full_name": request.data.get("full_name") or "",
            "birth_date": request.data.get("birth_date"),
        }
        snapshot = verify_recipient(
            iin,
            author_iin_hash=request.data.get("author_iin_hash") or "",
            identity=identity,
        )
        return Response(snapshot)
