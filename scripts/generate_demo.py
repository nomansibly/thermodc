"""Generate reproducible synthetic scenario telemetry with no external dependencies.

Usage: python -m scripts.generate_demo --output data/demo.sqlite
"""
import argparse
from thermodc.model import Inputs, simulate
from thermodc.scenarios import SCENARIOS
from thermodc.telemetry import connect, record

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default="data/demo.sqlite")
    args=parser.parse_args()
    connection=connect(args.output)
    try:
        for name,inputs in SCENARIOS.items():
            record(connection,name,inputs,simulate(inputs))
        print(f"Recorded {len(SCENARIOS)} synthetic scenarios in {args.output}")
    finally:
        connection.close()

if __name__=="__main__":
    main()
