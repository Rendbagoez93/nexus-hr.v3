"""
apps/apis/v1/authentication.py

Custom JWT authentication for DRF — extends SimpleJWT with Nexus-specific
claims (company_id, role) embedded directly in the access token payload.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuth
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class TokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token pair serializer that embeds `company_id` and `role` into the
    access token payload so the TenantMiddleware can read them without a DB hit.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed role always
        token["role"] = user.role
        # Embed company_id if the user belongs to a company
        if user.company_id is not None:
            token["company_id"] = user.company_id
        return token


class JWTAuthentication(BaseJWTAuth):
    """
    DRF authentication class. Extends SimpleJWT's base to validate
    that the requesting user is still active on each request.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, validated_token = result
        if not user.is_active:
            return None  # DRF will reject with 401
        return (user, validated_token)
