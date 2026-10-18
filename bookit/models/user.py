"""Custom user model identified by email, with only the columns the API needs."""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from .enums import UserRole


class UserManager(BaseUserManager):
    """Creates users with a lowercase email and a hashed password."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None, full_name: str, role: str = UserRole.CLIENT):
        """Create and save a user."""
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=self.normalize_email(email).lower(), full_name=full_name, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """Platform user; the role decides whether they book appointments or own businesses."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CLIENT)
    last_login = None  # JWT logins are stateless, so the inherited column is dropped

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        constraints = [models.CheckConstraint(condition=models.Q(role__in=UserRole.values), name="users_role_valid")]

    def __str__(self) -> str:
        """Return the email as the display name."""
        return self.email
