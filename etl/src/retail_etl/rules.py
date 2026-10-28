"""Load mapping rules and staging-table configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_rules(path: str | Path | None = None) -> dict[str, Any]:
    """Return the mapping rules (value mappings, defaults) as a dict."""
    with open(path or CONFIG_DIR / "mapping_rules.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_staging_config(path: str | Path | None = None) -> dict[str, Any]:
    """Return the gold -> Migration Cockpit staging-table configuration."""
    with open(path or CONFIG_DIR / "staging_tables.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def profit_center(site: str, rules: dict[str, Any]) -> str:
    """Derive the profit center for a site (DC01 -> 1100, ST07 -> 2107, WEB1 -> 3100)."""
    pc = rules["profit_center"]
    if site in pc:
        return pc[site]
    if site.startswith("ST") and site[2:].isdigit():
        return f"{pc['store_prefix']}{int(site[2:]):02d}"
    raise KeyError(f"No profit center rule for site {site}")
