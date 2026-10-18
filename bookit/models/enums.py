"""Enumerations stored as text columns."""
from django.db import models


class UserRole(models.TextChoices):
    """Who the user is on the platform."""

    CLIENT = "Client", "Client"
    BUSINESS_OWNER = "BusinessOwner", "Business owner"


class AppointmentStatus(models.TextChoices):
    """Lifecycle state of an appointment."""

    PENDING = "Pending", "Pending"
    CONFIRMED = "Confirmed", "Confirmed"
    CANCELLED = "Cancelled", "Cancelled"


class BusinessCategory(models.TextChoices):
    """Kind of business listed on the platform."""

    BARBER = "Barber", "Barber"
    BEAUTY = "Beauty", "Beauty"
    FITNESS = "Fitness", "Fitness"
    MASSAGE = "Massage", "Massage"
    PHYSIOTHERAPY = "Physiotherapy", "Physiotherapy"
    TUTORING = "Tutoring", "Tutoring"
