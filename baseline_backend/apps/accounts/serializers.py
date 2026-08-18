from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=12)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def validate_password(self, value: str) -> str:
        # Reuses Django's configured AUTH_PASSWORD_VALIDATORS (min length 12,
        # common-password check, similarity check) rather than duplicating
        # rules here.
        validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
