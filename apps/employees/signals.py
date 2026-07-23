"""
apps/employees/signals.py

Django signals for the employees app.

Wired here (not in attendance/) so that the attendance module stays decoupled
from employees — the attendance package never imports from apps.employees.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.employees.models import Employee


@receiver(post_save, sender=Employee)
def initialize_attendance_records(
    sender, instance: Employee, created: bool, **kwargs
) -> None:
    """Seed attendance records for a newly activated employee.

    Called whenever an Employee is saved with created=True (first insert).
    Deactivation / termination signals are handled separately in the
    attendance/services module so that deactivation logic stays with the
    attendance layer.

    Raises
    ------
    AttributeError
        If ``apps.attendance.services`` is not yet importable (e.g. circular
        import during initial migration). Safe to ignore at migrate time;
        the signal will fire correctly on the next Employee save.
    """
    if not created:
        return

    try:
        from apps.attendance.services import initialize_leave_balances

        initialize_leave_balances(employee=instance)
    except ImportError:
        # apps.attendance.services does not exist yet (early migration phase).
        # Log and re-raise only outside of a migration context.
        pass
