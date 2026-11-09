"""NI GPIB discovery and optional HP 6655A test at 12 V / 0.5 A maximum.

Run from an environment with IALib installed. Discovery is the default:
    python examples/hp6655a_ni.py
    python examples/hp6655a_ni.py --exercise GPIB0::5::INSTR

Requires NI-VISA and NI-488.2. IFC assumes this is the system controller;
do not run while another application is using the bus.
"""

import argparse
import time
from contextlib import closing

import pyvisa

from ialib.instruments.hp6655a import HP6655A, HP6655ACompatibility


def identify(interface, compatibility=False) -> str:
    identity = interface.query("ID?" if compatibility else "*IDN?").strip()
    if compatibility:
        for _ in range(10):
            if identity:
                break
            identity = interface.read().strip()
    print(f"{interface.resource_name}: {identity!r}")
    return identity


def exercise(interface, compatibility=False) -> None:
    identity = identify(interface, compatibility)
    fields = [field.strip().upper() for field in identity.split(",")]
    if compatibility:
        if identity != "ID HP6655A":
            raise RuntimeError("Refusing power test: legacy identity is not HP6655A")
    elif len(fields) < 2 or fields[1] not in ("6655A", "HP6655A"):
        raise RuntimeError("Refusing power test: instrument is not identified as 6655A")
    if not compatibility and fields[0] not in ("HEWLETT-PACKARD", "HP", "AGILENT TECHNOLOGIES",
                         "KEYSIGHT TECHNOLOGIES"):
        raise RuntimeError("Refusing power test: unrecognized manufacturer")
    supply = (HP6655ACompatibility if compatibility else HP6655A)(interface)
    supply.output = False
    try:
        # Do not clear protection trips or reset the instrument automatically.
        supply.set_iv(12.0, 0.5)
        voltage, current = supply.volt, supply.curr
        print(f"Set points: {voltage} V / {current} A")
        if not (0 <= voltage <= 12.0 and 0 <= current <= 0.5):
            raise RuntimeError("Refusing output enable: set point readback exceeds limit")
        supply.output = True
        time.sleep(1)
        print(f"Measured: {supply.v_meas} V / {supply.i_meas} A")
    finally:
        # Always attempt output-off, even if error queue checks fail.
        interface.write("OUT OFF" if compatibility else "OUTP OFF")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=int, default=0)
    parser.add_argument("--exercise", metavar="RESOURCE")
    parser.add_argument("--compatibility", action="store_true",
                        help="Use HP legacy commands without changing instrument language")
    args = parser.parse_args()
    with closing(pyvisa.ResourceManager()) as manager:
        with manager.open_resource(f"GPIB{args.board}::INTFC") as controller:
            controller.send_ifc()
        if args.exercise:
            if not args.exercise.startswith(f"GPIB{args.board}::"):
                parser.error("exercise resource must be on the selected GPIB board")
            with manager.open_resource(args.exercise) as interface:
                interface.timeout = 2000
                interface.write_termination = "\n"
                exercise(interface, args.compatibility)
        else:
            for resource in manager.list_resources(f"GPIB{args.board}::?*::INSTR"):
                try:
                    with manager.open_resource(resource) as interface:
                        interface.timeout = 2000
                        interface.write_termination = "\n"
                        identify(interface, args.compatibility)
                except pyvisa.errors.VisaIOError as error:
                    print(f"{resource}: {error}")


if __name__ == "__main__":
    main()
