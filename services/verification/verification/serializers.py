from rest_framework import serializers

from .models import FraudProfile, MedicalDiagnosis, MedicalRecord


class MedicalDiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalDiagnosis
        fields = ("name", "stage", "diagnosed_date")


class MedicalRecordSerializer(serializers.ModelSerializer):
    diagnoses = MedicalDiagnosisSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        fields = ("iin_masked", "full_name", "birth_date", "gender", "city", "clinic", "diagnoses")


class FraudProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudProfile
        fields = ("iin_masked", "full_name", "risk_score", "risk_level", "reasons")
