from rest_framework import serializers

from apps.core.models import Invitation, Membership


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "user_email", "user_full_name", "role", "status", "joined_at", "created_at"]
        read_only_fields = ["id", "user", "status", "joined_at", "created_at"]


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "status", "expires_at", "created_at"]
        read_only_fields = ["id", "status", "expires_at", "created_at"]


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
