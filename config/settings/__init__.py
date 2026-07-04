"""
Settings environment selector.

Set DJANGO_SETTINGS_MODULE to:
  - config.settings.local       (default — development)
  - config.settings.production   (production/staging)
"""

import os

_environment = os.environ.get("DJANGO_ENV", "local")

if _environment == "production":
    from .production import *  # noqa: F401, F403
else:
    from .local import *  # noqa: F401, F403
