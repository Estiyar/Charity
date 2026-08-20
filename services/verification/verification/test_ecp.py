import base64
import json
from datetime import datetime, timedelta, timezone

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs7 import PKCS7Options, PKCS7SignatureBuilder
from cryptography.x509.oid import NameOID

from ekomek_common.masking import mask_iin

from .models import EcpVerification

IIN = "880420301999"
CHALLENGE = "challenge-token-abc"


def make_test_cms(challenge=CHALLENGE, iin=IIN):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "KZ"),
            x509.NameAttribute(NameOID.COMMON_NAME, "ИВАНОВ ИВАН ИВАНОВИЧ"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, f"IIN{iin}"),
        ]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cms_der = (
        PKCS7SignatureBuilder()
        .set_data(challenge.encode("utf-8"))
        .add_signer(certificate, key, hashes.SHA256())
        .sign(serialization.Encoding.DER, [PKCS7Options.Binary])
    )
    return base64.b64encode(cms_der).decode("ascii")


class EcpVerificationAPITestCase(APITestCase):
    def test_dev_adapter_creates_immutable_record(self):
        payload = {
            "challenge": CHALLENGE,
            "iin": IIN,
            "full_name": "ИВАНОВ ИВАН ИВАНОВИЧ",
            "birth_date": "1988-04-20",
            "certificate_type": "individual",
            "serial_number": "dev",
            "issuer": "DEV NCA",
        }
        cms = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        response = self.client.post(
            "/internal/ecp/verify/",
            {"challenge": CHALLENGE, "cms": cms},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["full_name"], "ИВАНОВ ИВАН ИВАНОВИЧ")
        self.assertEqual(response.data["iin"], IIN)
        self.assertEqual(response.data["iin_masked"], mask_iin(IIN))
        self.assertEqual(EcpVerification.objects.count(), 1)
        record = EcpVerification.objects.get()
        self.assertNotEqual(record.iin_encrypted, IIN)

    @override_settings(ECP_ADAPTER="ncalayer", ECP_REQUIRE_NCA_ISSUER=False)
    def test_ncalayer_adapter_verifies_rsa_cms(self):
        cms = make_test_cms()
        response = self.client.post(
            "/internal/ecp/verify/",
            {"challenge": CHALLENGE, "cms": cms},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["iin"], IIN)
        self.assertEqual(response.data["full_name"], "ИВАНОВ ИВАН ИВАНОВИЧ")
        self.assertEqual(response.data["certificate_type"], "individual")
        self.assertTrue(response.data["serial_number"])
        self.assertTrue(response.data["issuer"])
        self.assertTrue(response.data["valid_from"])
        self.assertTrue(response.data["valid_to"])
        self.assertNotIn(IIN, str({k: v for k, v in response.data.items() if k != "iin"}))
        record = EcpVerification.objects.get(pk=response.data["verification_id"])
        record.full_name = "changed"
        with self.assertRaises(ValueError):
            record.save()

    @override_settings(ECP_ADAPTER="ncalayer", ECP_REQUIRE_NCA_ISSUER=False)
    def test_ncalayer_adapter_rejects_wrong_challenge(self):
        cms = make_test_cms()
        response = self.client.post(
            "/internal/ecp/verify/",
            {"challenge": "other-challenge", "cms": cms},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
