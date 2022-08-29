import time
import logging
from typing import Optional, cast

from ialib.instruments.types import InstrumentInterface

logger = logging.getLogger(__name__)


class Keithley7001:
    def __init__(self, ins: InstrumentInterface):
        self.ins = ins

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

    def open(self, slot: Optional[int] = None, chan: Optional[int] = None) -> None:
        if slot is None and chan is None:
            # Open all
            return self._write_data(":open all")
        if slot is None or chan is None:
            raise ValueError(f"Slot or chan not provided! (Slot: {slot}, Chan: {chan})")
        if slot not in [1, 2]:
            raise ValueError(
                f"Slot invalid must be 1 or 2! (Slot: {slot}, Chan: {chan})"
            )
        self._write_data(f":OPEN (@{slot}!{chan})")
        time.sleep(0.25)
        return None

    def close_sw(self, slot: int, chan: int) -> None:
        if slot not in [1, 2]:
            raise ValueError(
                f"Slot invalid must be 1 or 2! (Slot: {slot}, Chan: {chan})"
            )
        self._write_data(f":CLOS (@{slot}!{chan})")
        time.sleep(0.25)
        return None


if __name__ == "__main__":
    import pyvisa

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::26::INSTR")
    )

    ins = Keithley7001(ins_interface)
    ins.open()
    ins.close_sw(slot=1, chan=2)
