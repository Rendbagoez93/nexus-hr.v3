"""
apps/shared/context_processors.py

Template context processors for the web dashboard.
"""


def nexus_global(request) -> dict:
    """Add global Nexus context variables to all templates."""
    return {
        "nexus_app_name": "Nexus HR",
        "nexus_version": "1.0.0",
    }
