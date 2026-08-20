from .models import Beneficiary, Representation


class BeneficiaryRepository:
    def list_for_owner(self, owner_user_id):
        return Beneficiary.objects.filter(owner_user_id=owner_user_id, closed=False)

    def get_for_owner(self, owner_user_id, beneficiary_id):
        return Beneficiary.objects.filter(pk=beneficiary_id, owner_user_id=owner_user_id).first()

    def get_by_owner_and_hash(self, owner_user_id, iin_hash):
        return Beneficiary.objects.filter(owner_user_id=owner_user_id, iin_hash=iin_hash).first()

    def get(self, beneficiary_id):
        return Beneficiary.objects.filter(pk=beneficiary_id).first()


class RepresentationRepository:
    def get(self, representation_id):
        return Representation.objects.select_related("beneficiary").filter(pk=representation_id).first()

    def get_for_author_beneficiary(self, author_id, beneficiary_id):
        return Representation.objects.filter(author_id=author_id, beneficiary_id=beneficiary_id).first()

    def list_for_author(self, author_id):
        return Representation.objects.select_related("beneficiary").filter(author_id=author_id)

    def list_for_moderation(self, status_filter=None):
        queryset = Representation.objects.select_related("beneficiary").exclude(
            relationship_type="self"
        )
        if status_filter:
            return queryset.filter(verification_status=status_filter)
        return queryset.filter(
            verification_status__in=("pending", "manual_review")
        )
