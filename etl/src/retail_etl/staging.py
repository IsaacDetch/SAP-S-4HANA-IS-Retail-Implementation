"""Write gold datasets into SAP S/4HANA Migration Cockpit staging tables in SAP HANA.

Two routes are supported:
  * Databricks -> HANA over JDBC (SAP HANA JDBC driver ngdbc.jar installed on the cluster) – notebook 03.
  * Python -> HANA with hdbcli (this module) – used by the self-hosted runner for small objects and in tests
    with a stub connection.
The staging tables are truncated per object before each load so that every mock load is repeatable.
Staging-table names come from config/staging_tables.yaml (system-generated per migration project).
"""
from __future__ import annotations

from typing import Iterable, Protocol

import pandas as pd


class Cursor(Protocol):
    def execute(self, sql: str, params: Iterable | None = None): ...
    def executemany(self, sql: str, rows: list[tuple]): ...


def quote_ident(name: str) -> str:
    """HANA identifiers are double-quoted; generated staging names contain '/', so always quote."""
    return '"' + name.replace('"', '""') + '"'


def insert_sql(schema: str, table: str, columns: list[str]) -> str:
    cols = ", ".join(quote_ident(c) for c in columns)
    marks = ", ".join("?" for _ in columns)
    return f"INSERT INTO {quote_ident(schema)}.{quote_ident(table)} ({cols}) VALUES ({marks})"


def load_dataframe(cursor: Cursor, schema: str, table: str, df: pd.DataFrame, truncate: bool = True, batch_size: int = 10_000) -> int:
    """Truncate (optional) and bulk-insert a gold DataFrame; returns rows written."""
    if truncate:
        cursor.execute(f"TRUNCATE TABLE {quote_ident(schema)}.{quote_ident(table)}")
    if df.empty:
        return 0
    sql = insert_sql(schema, table, list(df.columns))
    rows = [tuple(None if pd.isna(v) else v for v in rec) for rec in df.itertuples(index=False, name=None)]
    for i in range(0, len(rows), batch_size):
        cursor.executemany(sql, rows[i:i + batch_size])
    return len(rows)


def connect_hana(host: str, port: int, user: str, password: str):
    """Open an hdbcli connection (pip install hdbcli). Credentials come from Azure Key Vault."""
    from hdbcli import dbapi  # imported lazily so unit tests do not need the driver
    return dbapi.connect(address=host, port=int(port), user=user, password=password, encrypt=True, sslValidateCertificate=True)
