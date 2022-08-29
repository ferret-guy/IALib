import logging
from typing import cast

from ialib.instruments.types import InstrumentInterface

logger = logging.getLogger(__name__)


class GWPSMPSU:
    def __init__(self, ins: InstrumentInterface):
        self.ins = ins

    def _write_data(self, dat: str) -> None:
        self.ins.write(dat)

    def _read_data(self) -> str:
        return self.ins.read()

    def _query_data(self, dat: str) -> str:
        return self.ins.query(dat)

    def set_iv(self, v: float, i: float):
        self._write_data(f":APPLY {v},{i}")

    @property
    def curr(self):
        """Current set point"""
        self._write_data(":CURR?")
        return float(self._read_data())

    @curr.setter
    def curr(self, val: float):
        """Current set point"""
        self._write_data(f":CURR {val}")

    @property
    def volt(self):
        """Volt set point"""
        self._write_data(":VOLT?")
        return float(self._read_data())

    @volt.setter
    def volt(self, val: float):
        """Volt set point"""
        self._write_data(f":VOLT {val}")

    @property
    def v_meas(self):
        self._write_data(":MEAS?")
        return float(self._read_data())

    @property
    def i_meas(self):
        self._write_data(":MEAS:CURR?")
        return float(self._read_data())

    @property
    def output(self):
        self._write_data(":OUTP:STAT?")
        return self._read_data()

    @output.setter
    def output(self, val):
        if val:
            self._write_data(":OUTP ON")
        else:
            self._write_data(":OUTP OFF")


if __name__ == "__main__":
    import pyvisa

    rm = pyvisa.ResourceManager()
    ins_interface = cast(
        pyvisa.resources.MessageBasedResource, rm.open_resource("GPIB0::7::INSTR")
    )

    ins = GWPSMPSU(ins_interface)

    ins.output = True
    print(ins.output)

    # ins.output = False
