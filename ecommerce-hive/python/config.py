# =============================================================================
# config.py
# Centralised configuration for Hive connection and project settings.
#
# All values can be overridden with environment variables.
# =============================================================================

import os

# ---------------------------------------------------------------------------
# Hive connection settings
# Override with environment variables in production or on different machines.
# ---------------------------------------------------------------------------

HIVE_HOST     = os.getenv("HIVE_HOST",     "localhost")
HIVE_PORT     = int(os.getenv("HIVE_PORT", "10000"))
HIVE_DATABASE = os.getenv("HIVE_DATABASE", "ecommerce")
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "hive")
HIVE_PASSWORD = os.getenv("HIVE_PASSWORD", "")         # empty = no auth
HIVE_AUTH     = os.getenv("HIVE_AUTH",     "NONE")     # NONE | NOSASL | LDAP | KERBEROS

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"

# ---------------------------------------------------------------------------
# Dashboard settings
# ---------------------------------------------------------------------------
DASHBOARD_TITLE = "E-Commerce Sales Analytics"
