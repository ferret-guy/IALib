"""Explicit hardware test: NI GPIB, master 5 / auto-parallel slave 6, SCPI.

Run with IALib installed: python tests/hp6655a_hardware.py
Programs at most 12 V, ramps master only to 7 V, master current 0.2 A,
slave programmed current zero. Replaces state 0 with output-off safe settings.
Requires SCPI mode on both supplies. Does not run during test discovery.
With a connected 10 ohm / 5 W load, use --load instead of the OVP ramp.
"""

import argparse
import time
from contextlib import ExitStack, closing

import pyvisa

from ialib.instruments.hp6655a import HP6655A


def run(load=False):
    with ExitStack() as stack:
        manager = stack.enter_context(closing(pyvisa.ResourceManager()))
        with manager.open_resource("GPIB0::INTFC") as controller:
            controller.send_ifc()
        resources = []
        supplies = []
        for address in (5, 6):
            interface = stack.enter_context(manager.open_resource(f"GPIB0::{address}::INSTR"))
            interface.timeout = 3000
            interface.write_termination = "\n"
            identity = interface.query("*IDN?").strip()
            assert identity.split(",")[:2] == ["HEWLETT-PACKARD", "6655A"], identity
            print(address, identity, flush=True)
            resources.append(interface)
            supplies.append(HP6655A(interface))
        master, slave = supplies

        def off():
            for interface in resources:
                try:
                    interface.write("OUTP OFF")
                except Exception as error:
                    print("OUTPUT-OFF FAILED:", error, flush=True)

        try:
            off()
            for index, supply in enumerate(supplies):
                supply.reset()
                assert supply.output is False
                supply.set_iv(0, .2 if index == 0 else 0)
                for enabled in (True, False):
                    supply.ocp = enabled
                    assert supply.ocp is enabled
                supply.ovp = 10
                assert abs(supply.ovp - 10) < .2
                assert supply.volt < .1
                assert supply.curr <= (.21 if index == 0 else .01)
                supply.clear_protection()
                assert supply.error is None
                resources[index].write("IALIB_INVALID_COMMAND")
                error = supply.error
                assert error is not None and -199 <= error.code <= -100
                print(index + 5, "command error readback", error.raw_str, flush=True)
                assert error.text and error.raw_str
                assert supply.error is None
                HP6655A(resources[index], error_check=False).volt = 0
                print(index + 5, "reset, OCP controls, OVP, set points, error checks PASS", flush=True)

            if load:
                master.set_iv(0, .2)
                slave.set_iv(12, 0)
                slave.output = True
                master.output = True
                master.volt = 6  # Even at full voltage, 10 ohms dissipates 3.6 W.
                time.sleep(.8)
                readings = [(s.v_meas, s.i_meas) for s in supplies]
                status = int(resources[0].query("STAT:OPER:COND?"))
                total_current = sum(i for _, i in readings)
                print("LOAD readings", readings, "total A", total_current,
                      "master operation status", status, flush=True)
                assert status & 1024, "Master did not enter constant-current mode"
                assert 0 < total_current <= .5, "Unexpected parallel current"
                assert all(0 <= v < 5.5 for v, _ in readings)
                assert abs(readings[0][0] / 10 - total_current) < .03
                print("CURRENT LIMIT PASS", flush=True)
                off()
                master.volt = 0
                for trip_index in (0, 1):
                    supplies[trip_index].ocp = True
                    slave.output = True
                    master.output = True
                    master.volt = 6
                    time.sleep(.8)
                    status = int(resources[trip_index].query("STAT:QUES:COND?"))
                    print("OCP", trip_index + 5, "status", status,
                          "readings", [(s.v_meas, s.i_meas) for s in supplies], flush=True)
                    assert status & 2, "OCP did not trip"
                    off()
                    master.volt = 0
                    supplies[trip_index].ocp = False
                    supplies[trip_index].clear_protection()
                    assert not int(resources[trip_index].query("STAT:QUES:COND?")) & 2
                    assert all(s.error is None for s in supplies)
                    print("OCP TRIP AND CLEAR PASS", trip_index + 5, flush=True)
                return

            for trip_index in (0, 1):
                off()
                master.set_iv(0, .2)
                slave.set_iv(12, 0)
                for index, supply in enumerate(supplies):
                    supply.ovp = 6 if index == trip_index else 10
                    supply.clear_protection()
                slave.output = True
                master.output = True
                assert master.output and slave.output
                tripped = False
                for voltage in (2, 4, 5.5, 6, 6.5, 7):
                    master.volt = voltage
                    time.sleep(.4)
                    readings = [(s.v_meas, s.i_meas) for s in supplies]
                    status = int(resources[trip_index].query("STAT:QUES:COND?"))
                    print("OVP", trip_index + 5, "set", master.volt,
                          "readings", readings, "status", status, flush=True)
                    assert all(abs(v) < 12 for v, _ in readings)
                    if status & 1:
                        tripped = True
                        break
                assert tripped, "Expected OVP trip did not occur"
                off()
                master.volt = 0
                supplies[trip_index].clear_protection()
                assert not int(resources[trip_index].query("STAT:QUES:COND?")) & 1
                assert all(s.error is None for s in supplies)
                print("OVP trip and protection clear PASS", trip_index + 5, flush=True)
        finally:
            off()
            for index, supply in enumerate(supplies):
                supply.set_iv(0, .2 if index == 0 else 0)
                supply.ocp = False
                supply.ovp = 10
                resources[index].write("*SAV 0")
                print(index + 5, "final OFF", not supply.output,
                      "V", supply.volt, "A", supply.curr, "error", supply.error, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", action="store_true", help="10 ohm / 5 W load connected")
    run(load=parser.parse_args().load)
