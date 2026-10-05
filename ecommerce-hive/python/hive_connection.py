# =============================================================================
# hive_connection.py
# Low-level Hive connectivity layer.
#
# Uses PyHive (pyhive[hive]) with a fallback message if the library is missing.
# All connection parameters come from config.py (which reads env vars).
# =============================================================================

import time
import logging
from contextlib import contextmanager
from typing import Tuple

import pandas as pd

try:
    from pyhive import hive
    from thrift.transport.TTransport import TTransportException
    PYHIVE_AVAILABLE = True
except ImportError:
    PYHIVE_AVAILABLE = False

from python.config import (
    HIVE_HOST, HIVE_PORT, HIVE_DATABASE,
    HIVE_USERNAME, HIVE_PASSWORD, HIVE_AUTH,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------

class HiveConnectionError(Exception):
    """Raised when the Hive server cannot be reached."""

class HiveQueryError(Exception):
    """Raised when a HiveQL query fails."""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _check_pyhive():
    if not PYHIVE_AVAILABLE:
        raise ImportError(
            "PyHive is not installed.  Run:  pip install pyhive[hive] thrift thrift-sasl"
        )


def get_connection():
    """
    Return a raw pyhive.hive.Connection.

    Raises HiveConnectionError if the server is unreachable.
    """
    _check_pyhive()
    try:
        conn = hive.connect(
            host=HIVE_HOST,
            port=HIVE_PORT,
            database=HIVE_DATABASE,
            username=HIVE_USERNAME,
            password=HIVE_PASSWORD or None,
            auth=HIVE_AUTH,
        )
        logger.debug("Connected to Hive at %s:%s/%s", HIVE_HOST, HIVE_PORT, HIVE_DATABASE)
        return conn
    except Exception as exc:
        raise HiveConnectionError(
            f"Cannot connect to Hive at {HIVE_HOST}:{HIVE_PORT}.\n"
            f"  • Is HiveServer2 running?  (start-all.sh then hive --service hiveserver2 &)\n"
            f"  • Check HIVE_HOST / HIVE_PORT env vars.\n"
            f"  Original error: {exc}"
        ) from exc


@contextmanager
def managed_connection():
    """Context manager that opens and closes a Hive connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def execute_query(query: str, params: Tuple = ()) -> pd.DataFrame:
    """
    Execute a HiveQL query and return the results as a Pandas DataFrame.

    Parameters
    ----------
    query  : HiveQL query string (use %s placeholders for parameters)
    params : optional tuple of parameter values

    Returns
    -------
    pd.DataFrame with column names taken from the cursor description.

    Raises
    ------
    HiveConnectionError  if the server is unreachable
    HiveQueryError       if the query fails
    """
    _check_pyhive()
    t0 = time.time()
    try:
        with managed_connection() as conn:
            cursor = conn.cursor()
            logger.debug("Executing query:\n%s", query.strip())
            cursor.execute(query, params)
            rows    = cursor.fetchall()
            columns = [desc[0].split(".")[-1] for desc in cursor.description] \
                      if cursor.description else []
            df = pd.DataFrame(rows, columns=columns)
            elapsed = time.time() - t0
            logger.info("Query returned %d rows in %.2fs", len(df), elapsed)
            return df
    except HiveConnectionError:
        raise
    except Exception as exc:
        raise HiveQueryError(
            f"Query failed:\n{query.strip()}\n\nReason: {exc}"
        ) from exc



def ping() -> bool:
    """
    Return True if HiveServer2 port is open, False otherwise.

    Uses a raw TCP socket check instead of a full PyHive connection so that
    the thrift library does NOT print 'Could not connect to ...' messages to
    stderr when the server is simply not running.
    """
    import socket
    try:
        sock = socket.create_connection((HIVE_HOST, HIVE_PORT), timeout=2)
        sock.close()
        return True
    except OSError:
        return False
