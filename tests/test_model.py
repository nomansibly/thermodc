import math
import pytest
from thermodc.model import Inputs, simulate

def test_baseline_energy_balance():
    r = simulate(Inputs())
    assert r.it_kw == pytest.approx(78)
    assert r.cooling_kw == pytest.approx(78/3.5)
    assert r.auxiliary_kw == pytest.approx(7)
    assert r.facility_kw == pytest.approx(r.it_kw+r.cooling_kw+r.auxiliary_kw)
    assert r.pue == pytest.approx(r.facility_kw/r.it_kw)
    assert r.daily_kwh == pytest.approx(24*r.facility_kw)
    assert len(r.rack_inlet_c) == 12

def test_load_increases_temperature():
    low=simulate(Inputs(utilization_pct=20))
    high=simulate(Inputs(utilization_pct=100))
    assert high.max_inlet_c > low.max_inlet_c
    assert high.it_kw > low.it_kw

def test_less_airflow_increases_max_temperature():
    slow=simulate(Inputs(airflow_pct=40))
    fast=simulate(Inputs(airflow_pct=150))
    assert slow.max_inlet_c > fast.max_inlet_c

def test_recirculation_increases_inlets():
    clean=simulate(Inputs(recirculation_pct=0))
    mixed=simulate(Inputs(recirculation_pct=50))
    assert mixed.max_inlet_c > clean.max_inlet_c

def test_better_cop_reduces_cooling_energy():
    bad=simulate(Inputs(cooling_cop=2))
    good=simulate(Inputs(cooling_cop=6))
    assert good.cooling_kw < bad.cooling_kw
    assert good.pue < bad.pue

@pytest.mark.parametrize("field,value",[
    ("airflow_pct",0), ("cooling_cop",0), ("recirculation_pct",90),
    ("utilization_pct",101), ("supply_c",float("nan")),
    ("outdoor_c",float("inf")),
])
def test_invalid_inputs_rejected(field,value):
    kwargs={field:value}
    with pytest.raises(ValueError):
        simulate(Inputs(**kwargs))

def test_all_scenarios_finite():
    from thermodc.scenarios import SCENARIOS
    for scenario in SCENARIOS.values():
        result=simulate(scenario)
        assert math.isfinite(result.pue)
        assert result.facility_kw > result.it_kw
