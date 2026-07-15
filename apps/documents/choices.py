"""
apps/documents/choices.py

TextChoices for EmployeeDocument enumerations.
"""

from django.db.models import TextChoices


class DocumentType(TextChoices):
    """Type of document attached to an Employee."""

    KTP = "ktp", "KTP"
    NPWP = "npwp", "NPWP"
    CONTRACT = "contract", "Contract"
    IJAZAH = "ijazah", "Ijazah"
    SIM = "sim", "SIM"
    SERTIFIKAT = "sertifikat", "Sertifikat"
    OTHER = "other", "Other"
