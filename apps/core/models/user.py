"""
apps/core/models/user.py

AuthUser — custom user model extending AbstractBaseUser.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.shared.mixins.timestamped import TimestampedModel


class AuthUserManager(BaseUserManager):
    """Custom manager for AuthUser."""

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("role", "platform_admin")
        extra_fields.setdefault("company_id", None)
        return self.create_user(email, password, **extra_fields)


class AuthUser(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    """
    Custom user model for Nexus.

    - Email is the login identifier (unique)
    - Role controls permission level
    - company FK links to tenant (nullable for platform admins)
    """

    ROLE_CHOICES = [
        ("platform_admin", "Platform Admin"),
        ("hr_admin", "HR Admin"),
        ("manager", "Manager"),
        ("employee", "Employee"),
        ("hse_officer", "HSE Officer"),
    ]

    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)

    objects = AuthUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "core_auth_user"
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email


class RefreshToken(models.Model):
    """
    Tracks issued refresh tokens for revocation support.

    The actual token is stored as a one-way hash in `token_hash`.
    """

    user = models.ForeignKey(
        "core.AuthUser",
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    device_id = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_refresh_token"
        indexes = [
            models.Index(fields=["user", "device_id"]),
            models.Index(fields=["user", "is_revoked"]),
        ]

    def __str__(self) -> str:
        return f"RefreshToken({self.user.email}, revoked={self.is_revoked})"
