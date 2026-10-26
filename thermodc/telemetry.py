"""SQLite telemetry: intentionally local; no credentials or cloud services."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .model import Inputs, Result

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp_utc TEXT NOT NULL,
  scenario TEXT NOT NULL,
  utilization_pct REAL NOT NULL,
  supply_c REAL NOT NULL,
  airflow_pct REAL NOT NULL,
  cooling_cop REAL NOT NULL,
  recirculation_pct REAL NOT NULL,
  outdoor_c REAL NOT NULL,
  it_kw REAL NOT NULL,
  cooling_kw REAL NOT NULL,
  facility_kw REAL NOT NULL,
  pue REAL NOT NULL,
  max_inlet_c REAL NOT NULL,
  hot_racks INTEGER NOT NULL,
  rack_inlet_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry(timestamp_utc);
"""

def connect(path: str | Path = "data/thermodc.sqlite") -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    return connection

def record(connection: sqlite3.Connection, scenario: str, inputs: Inputs, result: Result) -> None:
    connection.execute(
        """INSERT INTO telemetry
        (timestamp_utc,scenario,utilization_pct,supply_c,airflow_pct,cooling_cop,
         recirculation_pct,outdoor_c,it_kw,cooling_kw,facility_kw,pue,max_inlet_c,
         hot_racks,rack_inlet_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (datetime.now(timezone.utc).isoformat(), scenario, inputs.utilization_pct,
         inputs.supply_c, inputs.airflow_pct, inputs.cooling_cop,
         inputs.recirculation_pct, inputs.outdoor_c, result.it_kw,
         result.cooling_kw, result.facility_kw, result.pue,
         result.max_inlet_c, result.hot_racks, json.dumps(result.rack_inlet_c))
    )
    connection.commit()

def history(connection: sqlite3.Connection, limit: int = 200) -> list[dict]:
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be 1..10000")
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(row) for row in reversed(rows)]
