import json
import pytest
from thermodc.model import Inputs, simulate
from thermodc.telemetry import connect, record, history

def test_telemetry_roundtrip(tmp_path):
    connection=connect(tmp_path/"telemetry.sqlite")
    try:
        inputs=Inputs()
        result=simulate(inputs)
        record(connection,"Normal operation",inputs,result)
        rows=history(connection)
        assert len(rows)==1
        assert rows[0]["scenario"]=="Normal operation"
        assert rows[0]["pue"]==pytest.approx(result.pue)
        assert len(json.loads(rows[0]["rack_inlet_json"]))==12
    finally:
        connection.close()

def test_limit_validation(tmp_path):
    connection=connect(tmp_path/"test.sqlite")
    try:
        with pytest.raises(ValueError):
            history(connection, -1)
    finally:
        connection.close()
