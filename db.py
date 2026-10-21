"""
db.py — SQL Server connection for the HASBAH sales feed.

All connection settings come from environment variables (see .env.example);
a local .env file is loaded automatically. The engine is created lazily so
importing this module never opens a connection or fails when DATA_SOURCE=excel.
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()

_engine: Engine | None = None


def _conn_str() -> str:
    required = ["MSSQL_HOST", "MSSQL_DB", "MSSQL_USER", "MSSQL_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing MSSQL settings in environment/.env: {', '.join(missing)}")

    odbc = (
        f"DRIVER={{{os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')}}};"
        f"SERVER={os.environ['MSSQL_HOST']},{os.getenv('MSSQL_PORT', '1433')};"
        f"DATABASE={os.environ['MSSQL_DB']};"
        f"UID={os.environ['MSSQL_USER']};"
        f"PWD={os.environ['MSSQL_PASSWORD']};"
        f"Encrypt={os.getenv('MSSQL_ENCRYPT', 'yes')};"
        f"TrustServerCertificate={os.getenv('MSSQL_TRUST_CERT', 'yes')};"
        f"Connection Timeout={os.getenv('MSSQL_TIMEOUT', '30')};"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_conn_str(), pool_pre_ping=True)
    return _engine


if __name__ == "__main__":
    # Connectivity check:  python db.py
    with get_engine().connect() as c:
        print(c.exec_driver_sql("SELECT @@SERVERNAME, DB_NAME(), @@VERSION").fetchone())
