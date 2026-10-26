"""Educational steady-state data-center energy and thermal calculations.

Not CFD, a transient model, or a safety-qualified engineering tool.
"""
from dataclasses import asdict, dataclass
from math import isfinite

RACK_FACTORS = (0.65, 0.80, 1.05, 1.23, 1.42, 0.95,
                1.10, 1.30, 1.52, 0.85, 1.18, 1.65)
AIR_DENSITY = 1.2                  # kg/m3, fixed
AIR_SPECIFIC_HEAT = 1005.0        # J/(kg K), fixed
DESIGN_AIRFLOW = 12.0             # m3/s
INSTALLED_IT_KW = 120.0
REFERENCE_INLET_C = 27.0          # illustrative only

@dataclass(frozen=True)
class Inputs:
    utilization_pct: float = 65
    supply_c: float = 20
    airflow_pct: float = 100
    cooling_cop: float = 3.5
    recirculation_pct: float = 15
    outdoor_c: float = 15

    def validate(self) -> None:
        bounds = {
            "utilization_pct": (10, 100),
            "supply_c": (16, 28),
            "airflow_pct": (40, 150),
            "cooling_cop": (1.5, 7),
            "recirculation_pct": (0, 50),
            "outdoor_c": (-20, 40),
        }
        for field, (low, high) in bounds.items():
            value = getattr(self, field)
            if not isfinite(value) or not low <= value <= high:
                raise ValueError(f"{field} must be finite and within [{low}, {high}]")

@dataclass(frozen=True)
class Result:
    it_kw: float
    cooling_kw: float
    auxiliary_kw: float
    facility_kw: float
    daily_kwh: float
    pue: float
    delta_t_c: float
    return_c: float
    rack_inlet_c: tuple[float, ...]
    max_inlet_c: float
    hot_racks: int
    status: str

    def as_dict(self) -> dict:
        value = asdict(self)
        value["rack_inlet_c"] = list(self.rack_inlet_c)
        return value

def simulate(inputs: Inputs) -> Result:
    """Compute a deterministic steady-state operating point.

    Assumptions:
    * 100% IT electrical power becomes heat.
    * Delta-T = IT watts / (rho * Vdot * cp).
    * Recirculation increases rack inlet temperature; rack factors are synthetic.
    * Cooling electricity = IT heat / constant user-entered COP.
    * Fan/auxiliary electricity = 3 + 4*(airflow/design)^3 kW.
    * Outdoor temperature is recorded, not used to change COP.
    * 27°C is an illustrative user-interface reference, not universal safety limit.
    """
    inputs.validate()
    it_kw = INSTALLED_IT_KW * inputs.utilization_pct / 100
    flow = DESIGN_AIRFLOW * inputs.airflow_pct / 100
    delta = it_kw * 1000 / (flow * AIR_DENSITY * AIR_SPECIFIC_HEAT)
    recirculation = inputs.recirculation_pct / 100
    inlet = inputs.supply_c + delta * recirculation
    rack_temps = tuple(
        inputs.supply_c + delta * recirculation * factor
        + delta * 0.055 * (factor - 0.65)
        for factor in RACK_FACTORS
    )
    max_inlet = max(rack_temps)
    cooling_kw = it_kw / inputs.cooling_cop
    auxiliary_kw = 3 + 4 * (inputs.airflow_pct / 100) ** 3
    facility_kw = it_kw + cooling_kw + auxiliary_kw
    status = ("HIGH RISK" if max_inlet > 32 else
              "ELEVATED" if max_inlet > REFERENCE_INLET_C else "WITHIN REFERENCE")
    return Result(
        it_kw=it_kw, cooling_kw=cooling_kw, auxiliary_kw=auxiliary_kw,
        facility_kw=facility_kw, daily_kwh=facility_kw * 24,
        pue=facility_kw / it_kw, delta_t_c=delta,
        return_c=inlet + delta, rack_inlet_c=rack_temps,
        max_inlet_c=max_inlet,
        hot_racks=sum(temp > REFERENCE_INLET_C for temp in rack_temps),
        status=status,
    )
